from pathlib import Path
from unittest.mock import MagicMock
import subprocess
import pytest

from src.loki.engine.replayer import IncidentReplayer
from src.loki.engine.healer import CodeHealer


class TestIncidentReplayer:
    def test_missing_repro_script(self, tmp_path):
        replayer = IncidentReplayer(runs_dir=str(tmp_path))
        res = replayer.replay_test(tmp_path)
        assert res["success"] is False
        assert "Reproduction script missing" in res["error"]

    def test_successful_clean_run_no_crashes(self, tmp_path, monkeypatch):
        script = tmp_path / "repro_test.py"
        script.write_text("print('All good')", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "✔ [LOKI REPRO] No crashes detected. Bug might be resolved."
        mock_proc.stderr = ""
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_proc))

        replayer = IncidentReplayer(runs_dir=str(tmp_path))
        res = replayer.replay_test(tmp_path)
        assert res["success"] is True
        assert res["reproduced"] is False

    def test_genuine_crash_reproduced(self, tmp_path, monkeypatch):
        script = tmp_path / "repro_test.py"
        script.write_text("print('Crash')", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "💥 [LOKI REPRO] CRASH SUCCESSFULLY REPRODUCED!\n  • TypeError: null is not an object"
        mock_proc.stderr = ""
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_proc))

        replayer = IncidentReplayer(runs_dir=str(tmp_path))
        res = replayer.replay_test(tmp_path)
        assert res["success"] is True
        assert res["reproduced"] is True

    def test_internal_script_failure_not_reported_as_reproduced(self, tmp_path, monkeypatch):
        script = tmp_path / "repro_test.py"
        script.write_text("raise RuntimeError()", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "⚡ [LOKI REPRO] Navigating to target..."
        mock_proc.stderr = "Traceback (most recent call last):\n  File 'repro_test.py', line 12, in <module>\nplaywright._impl._errors.TimeoutError: Page.goto timeout"
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_proc))

        replayer = IncidentReplayer(runs_dir=str(tmp_path))
        res = replayer.replay_test(tmp_path)
        # Crucial invariant: Must NOT report reproduced=True
        assert res["success"] is False
        assert res["reproduced"] is False
        assert "Reproduction script encountered an execution error" in res["error"]

    def test_script_exit_code_2_error(self, tmp_path, monkeypatch):
        script = tmp_path / "repro_test.py"
        script.write_text("error", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.returncode = 2
        mock_proc.stdout = ""
        mock_proc.stderr = "❌ [LOKI REPRO ERROR] Test script execution failed: Browser closed"
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_proc))

        replayer = IncidentReplayer(runs_dir=str(tmp_path))
        res = replayer.replay_test(tmp_path)
        assert res["success"] is False
        assert res["reproduced"] is False


class TestCodeHealerVerifyFix:
    def test_verify_fix_success_removes_backup(self, tmp_path):
        repro_script = tmp_path / "repro_test.py"
        repro_script.write_text("# dummy", encoding="utf-8")
        target = tmp_path / "app.py"
        target.write_text("x = 1", encoding="utf-8")
        backup = tmp_path / "app.py.loki.bak"
        backup.write_text("x = 0", encoding="utf-8")

        healer = CodeHealer(runs_dir=str(tmp_path))
        mock_replayer = MagicMock()
        mock_replayer.replay_test.return_value = {
            "success": True,
            "reproduced": False,
            "stdout": "✔ [LOKI REPRO] No crashes detected.",
        }
        healer.replayer = mock_replayer

        res = healer.verify_fix(tmp_path, backup_file=backup, target_file=target)
        assert res["verified"] is True
        assert not backup.exists()
        assert target.read_text(encoding="utf-8") == "x = 1"

    def test_verify_fix_reproduced_rolls_back(self, tmp_path):
        repro_script = tmp_path / "repro_test.py"
        repro_script.write_text("# dummy", encoding="utf-8")
        target = tmp_path / "app.py"
        target.write_text("fixed_code_still_crashes()", encoding="utf-8")
        backup = tmp_path / "app.py.loki.bak"
        backup.write_text("original_broken_code()", encoding="utf-8")

        healer = CodeHealer(runs_dir=str(tmp_path))
        mock_replayer = MagicMock()
        mock_replayer.replay_test.return_value = {
            "success": True,
            "reproduced": True,
            "stdout": "💥 [LOKI REPRO] CRASH SUCCESSFULLY REPRODUCED!",
        }
        healer.replayer = mock_replayer

        res = healer.verify_fix(tmp_path, backup_file=backup, target_file=target)
        assert res["verified"] is False
        assert res["rolled_back"] is True
        # Target must be restored from backup
        assert target.read_text(encoding="utf-8") == "original_broken_code()"
        assert not backup.exists()

    def test_verify_fix_does_not_rollback_on_script_execution_error(self, tmp_path):
        repro_script = tmp_path / "repro_test.py"
        repro_script.write_text("# dummy", encoding="utf-8")
        target = tmp_path / "app.py"
        target.write_text("valid_patch_applied()", encoding="utf-8")
        backup = tmp_path / "app.py.loki.bak"
        backup.write_text("original_unpatched_code()", encoding="utf-8")

        healer = CodeHealer(runs_dir=str(tmp_path))
        mock_replayer = MagicMock()
        mock_replayer.replay_test.return_value = {
            "success": False,
            "reproduced": False,
            "error": "Reproduction script encountered an execution error: Page.goto timeout",
        }
        healer.replayer = mock_replayer

        res = healer.verify_fix(tmp_path, backup_file=backup, target_file=target)
        # Crucial invariant: Must NOT roll back when replay failed to run cleanly
        assert res["verified"] is False
        assert res["rolled_back"] is False
        assert res.get("error") is True
        assert "[REPLAY ERROR]" in res["message"]
        # Source code remains patched and backup remains intact
        assert target.read_text(encoding="utf-8") == "valid_patch_applied()"
        assert backup.exists()
