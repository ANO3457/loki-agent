import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any


class IncidentReplayer:
    """Manages the replay and visual verification of previously captured incidents."""

    def __init__(self, runs_dir: str = ".loki/runs"):
        self.runs_dir = Path(runs_dir)

    def get_run_dir(self, run_id: Optional[str] = None) -> Optional[Path]:
        """Resolves target run directory by ID or falls back to the most recent one."""
        if not self.runs_dir.exists():
            return None

        if run_id:
            target = self.runs_dir / run_id
            return target if target.exists() and target.is_dir() else None

        # Sort runs by modification time descending
        run_dirs = [d for d in self.runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
        if not run_dirs:
            return None
        run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        return run_dirs[0]

    def replay_test(self, run_dir: Path) -> Dict[str, Any]:
        """Executes the generated reproduction script for the incident."""
        repro_script = run_dir / "repro_test.py"
        if not repro_script.exists():
            return {"success": False, "error": f"Reproduction script missing: {repro_script}"}

        # Run with current Python executable in visible mode with UTF-8 encoding
        cmd = [sys.executable, str(repro_script)]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=30,
            )
            # repro_test.py exits with 1 when crash is reproduced, and 0 when no crashes
            return {
                "success": True,
                "reproduced": result.returncode == 1,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Replay execution timed out after 30 seconds."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_video(self, run_dir: Path) -> Dict[str, Any]:
        """Opens the recorded video artifact in the OS default video player."""
        video_file = run_dir / "replay.webm"
        if not video_file.exists():
            return {"success": False, "error": f"Video artifact missing: {video_file}"}

        try:
            if os.name == "nt":  # Windows
                os.startfile(str(video_file.resolve()))
            elif sys.platform == "darwin":  # macOS
                subprocess.Popen(["open", str(video_file.resolve())])
            else:  # Linux
                subprocess.Popen(["xdg-open", str(video_file.resolve())])
            return {"success": True, "video_path": str(video_file)}
        except Exception as e:
            return {"success": False, "error": str(e)}
