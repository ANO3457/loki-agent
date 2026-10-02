import json
from unittest.mock import MagicMock
import pytest

from src.loki.engine.api_chaos import (
    ApiChaosConfig,
    ApiChaosEngine,
    ApiFaultEvent,
    mutate_json_payload,
    strip_schema_keys,
)


class TestMutateJsonPayload:
    def test_mutate_dict_primitive_types(self):
        data = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "score": 99.5,
            "roles": ["admin", "editor"],
        }
        # Run multiple times to observe mutation coverage
        has_mutated = False
        for _ in range(10):
            mutated = mutate_json_payload(data, monster_len=100)
            assert isinstance(mutated, dict)
            if mutated != data:
                has_mutated = True
        assert has_mutated, "Expected data to be mutated across 10 iterations"

    def test_mutate_empty_dict(self):
        res = mutate_json_payload({})
        assert isinstance(res, dict)
        assert "_corrupted_by_loki" in res

    def test_mutate_nested_structure(self):
        nested = {
            "user": {
                "profile": {
                    "bio": "Developer",
                    "followers": 100,
                }
            },
            "tags": ["python", "ai"],
        }
        res = mutate_json_payload(nested, monster_len=50)
        assert isinstance(res, dict)

    def test_mutate_list(self):
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        res = mutate_json_payload(items)
        assert isinstance(res, list)

    def test_mutate_empty_list(self):
        res = mutate_json_payload([])
        assert isinstance(res, list)
        assert len(res) == 1
        assert "_corrupted_item" in res[0]


class TestStripSchemaKeys:
    def test_strip_dict_keys(self):
        data = {
            "id": 123,
            "username": "tester",
            "email": "test@example.com",
            "profile": {"avatar": "url"},
        }
        stripped, dropped = strip_schema_keys(data)
        assert len(dropped) >= 1
        for k in dropped:
            assert k not in stripped
        assert len(stripped) < len(data)

    def test_strip_empty_dict(self):
        stripped, dropped = strip_schema_keys({})
        assert stripped == {}
        assert dropped == []

    def test_strip_list(self):
        stripped, dropped = strip_schema_keys([1, 2, 3])
        assert stripped == []
        assert dropped == ["_all_items_stripped"]


class TestApiChaosEngineEligibility:
    def test_ignores_static_assets(self):
        engine = ApiChaosEngine()
        for ext in [".js", ".css", ".png", ".jpg", ".svg", ".woff2", ".ico"]:
            req = MagicMock()
            req.url = f"https://example.com/assets/bundle{ext}"
            req.resource_type = "script" if ext == ".js" else "stylesheet"
            assert engine.is_eligible(req) is False

    def test_ignores_non_http(self):
        engine = ApiChaosEngine()
        for scheme in ["data:text/html,test", "chrome://version", "blob:https://example.com/abc"]:
            req = MagicMock()
            req.url = scheme
            req.resource_type = "fetch"
            assert engine.is_eligible(req) is False

    def test_accepts_fetch_and_xhr(self):
        engine = ApiChaosEngine()
        for r_type in ["fetch", "xhr"]:
            req = MagicMock()
            req.url = "https://example.com/data/query"
            req.resource_type = r_type
            assert engine.is_eligible(req) is True

    def test_accepts_api_patterns(self):
        engine = ApiChaosEngine()
        for url in [
            "https://example.com/api/v1/users",
            "https://example.com/graphql",
            "https://example.com/rest/items",
            "https://example.com/services/auth",
            "https://example.com/config.json",
        ]:
            req = MagicMock()
            req.url = url
            req.resource_type = "other"
            assert engine.is_eligible(req) is True


class TestApiChaosEngineFaultInjection:
    def test_inject_status_code(self):
        config = ApiChaosConfig(enabled=True, fault_rate=1.0, fault_types=["status_code"], status_codes=[500])
        engine = ApiChaosEngine(config)

        route = MagicMock()
        request = MagicMock()
        request.url = "https://example.com/api/checkout"
        request.method = "POST"
        request.resource_type = "fetch"

        engine._handle_route(route, request)

        assert len(engine.injected_faults) == 1
        fault = engine.injected_faults[0]
        assert fault.fault_type == "status_code"
        assert fault.injected_status == 500
        assert fault.url == "https://example.com/api/checkout"

        route.fulfill.assert_called_once()
        call_kwargs = route.fulfill.call_args[1]
        assert call_kwargs["status"] == 500
        assert call_kwargs["content_type"] == "application/json"

    def test_inject_empty_response(self):
        config = ApiChaosConfig(enabled=True, fault_rate=1.0, fault_types=["empty_response"])
        engine = ApiChaosEngine(config)

        route = MagicMock()
        request = MagicMock()
        request.url = "https://example.com/api/items"
        request.method = "GET"
        request.resource_type = "fetch"

        engine._handle_route(route, request)

        assert len(engine.injected_faults) == 1
        assert engine.injected_faults[0].fault_type == "empty_response"
        route.fulfill.assert_called_once_with(
            status=200,
            content_type="application/json",
            body=b"{}",
            headers={"x-loki-fault": "empty_response"},
        )

    def test_inject_corrupt_json(self):
        config = ApiChaosConfig(enabled=True, fault_rate=1.0, fault_types=["corrupt_json"])
        engine = ApiChaosEngine(config)

        real_response = MagicMock()
        real_response.status = 200
        real_response.headers = {"content-type": "application/json; charset=utf-8"}
        real_response.body.return_value = json.dumps({"user": "John", "balance": 1500}).encode("utf-8")

        route = MagicMock()
        route.fetch.return_value = real_response

        request = MagicMock()
        request.url = "https://example.com/api/user/1"
        request.method = "GET"
        request.resource_type = "fetch"

        engine._handle_route(route, request)

        assert len(engine.injected_faults) == 1
        assert engine.injected_faults[0].fault_type == "corrupt_json"
        route.fulfill.assert_called_once()
        call_kwargs = route.fulfill.call_args[1]
        assert "x-loki-fault" in call_kwargs["headers"]
        assert call_kwargs["headers"]["x-loki-fault"] == "corrupt_json"

    def test_inject_schema_strip(self):
        config = ApiChaosConfig(enabled=True, fault_rate=1.0, fault_types=["schema_strip"])
        engine = ApiChaosEngine(config)

        real_response = MagicMock()
        real_response.status = 200
        real_response.headers = {"content-type": "application/json"}
        real_response.body.return_value = json.dumps({
            "status": "ok",
            "data": {"id": 1},
            "pagination": {"page": 1},
        }).encode("utf-8")

        route = MagicMock()
        route.fetch.return_value = real_response

        request = MagicMock()
        request.url = "https://example.com/api/products"
        request.method = "GET"
        request.resource_type = "fetch"

        engine._handle_route(route, request)

        assert len(engine.injected_faults) == 1
        assert engine.injected_faults[0].fault_type == "schema_strip"
        route.fulfill.assert_called_once()


class TestSummaryAndRepro:
    def test_summary_telemetry(self):
        engine = ApiChaosEngine()
        engine.injected_faults.append(
            ApiFaultEvent(url="https://example.com/api/test", method="GET", fault_type="status_code", injected_status=500)
        )
        engine.injected_faults.append(
            ApiFaultEvent(url="https://example.com/api/test2", method="POST", fault_type="empty_response", injected_status=200)
        )

        summary = engine.get_summary()
        assert summary["total_faults_injected"] == 2
        assert summary["faults_by_type"]["status_code"] == 1
        assert summary["faults_by_type"]["empty_response"] == 1
        assert len(summary["attacked_endpoints"]) == 2

    def test_generate_repro_routes(self):
        engine = ApiChaosEngine()
        engine.injected_faults.append(
            ApiFaultEvent(
                url="https://example.com/api/v1",
                method="GET",
                fault_type="status_code",
                injected_status=502,
                details={"error_payload": {"err": "Bad Gateway"}},
            )
        )
        repro = engine.generate_repro_routes()
        assert len(repro) == 1
        assert repro[0]["url"] == "https://example.com/api/v1"
        assert repro[0]["status"] == 502
