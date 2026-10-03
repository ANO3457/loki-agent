from pathlib import Path

import pytest

from src.loki.engine.html_reporter import HTMLReporter


@pytest.mark.parametrize("status", [None, 123, "PASSED", "VIOLATED"])
def test_rule_status_is_rendered_without_type_errors(tmp_path: Path, status):
    output = tmp_path / "report.html"
    HTMLReporter.generate({"rules_evaluations": [{"status": status}]}, output)
    rendered = output.read_text(encoding="utf-8")
    assert ("UNKNOWN" if status is None else str(status)) in rendered


@pytest.mark.parametrize("status", [None, "MUTATED", "200", "500"])
def test_concurrency_status_is_cast_before_counting_successes(tmp_path: Path, status):
    output = tmp_path / "report.html"
    response = {"method": "POST", "status": status}
    HTMLReporter.generate(
        {"concurrency": 2, "concurrency_lanes": [
            {"lane": 1, "responses": [response]},
            {"lane": 2, "responses": [response]},
        ]},
        output,
    )
    rendered = output.read_text(encoding="utf-8")
    assert ("2 lanes recorded a successful response" in rendered) == (status == "200")


@pytest.mark.parametrize(
    "status, expected", [(None, "Mutated"), ("MUTATED", "MUTATED"),
                         ("CORRUPTED", "CORRUPTED"), ("<fault>", "&lt;fault&gt;"),
                         ("503", 'badge-danger">503'), (200, 'badge-success">200')]
)
def test_fault_status_is_safe_and_retains_its_display_value(tmp_path: Path, status, expected):
    output = tmp_path / "report.html"
    HTMLReporter.generate({"api_faults": [{"status": status}]}, output)
    assert expected in output.read_text(encoding="utf-8")
