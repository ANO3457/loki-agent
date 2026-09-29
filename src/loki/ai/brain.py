import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import litellm
litellm.suppress_debug_info = True
from src.loki.engine.sandbox import IncidentReport
from src.loki.engine.healer import CodeHealer
from src.loki.config import resolve_model


class AIBrain:
    """Coordinates AI-driven crash diagnostics and patch synthesis."""

    def __init__(self, runs_dir: str = ".loki/runs"):
        self.runs_dir = Path(runs_dir)

    def get_latest_run_dir(self) -> Optional[Path]:
        """Finds the most recent incident run directory."""
        if not self.runs_dir.exists():
            return None
        run_dirs = [d for d in self.runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
        if not run_dirs:
            return None
        # Sort by folder creation / modification time descending
        run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        return run_dirs[0]

    def diagnose_and_fix(self, run_id: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes an incident using LLM reasoning and proposes an exact patch."""
        # 1. Resolve run directory
        if run_id:
            target_dir = self.runs_dir / run_id
        else:
            target_dir = self.get_latest_run_dir()

        if not target_dir or not (target_dir / "incident.json").exists():
            return {"error": f"No valid incident found in '{target_dir}'"}

        # 2. Read incident metadata
        with open(target_dir / "incident.json", "r", encoding="utf-8") as f:
            incident_data = json.load(f)

        # 3. Read the source file most likely responsible for the crash
        source_context = ""
        source_file = CodeHealer(runs_dir=str(self.runs_dir)).resolve_source_file(incident_data)
        if source_file and source_file.exists():
            try:
                source_context = f"\nRelevant source file (`{source_file}`):\n```\n{source_file.read_text(encoding='utf-8')}\n```"
            except (OSError, UnicodeDecodeError):
                source_context = ""

        prompt = f"""You are LOKI, an elite AI Chaos & Software Quality Engineer.
Analyze this real-world application crash and synthesize a precise diagnosis and fix.

### Incident Metadata:
- Target URL: {incident_data.get('target_url')}
- Attacker Persona: {incident_data.get('persona')}
- Unhandled Crashes: {json.dumps(incident_data.get('crashes'), indent=2)}
- HTTP Errors: {json.dumps(incident_data.get('http_errors'), indent=2)}
- Attacker Actions: {incident_data.get('actions_executed_count')} actions recorded
{source_context}

Please provide your answer with the following structure:
1. **Root Cause Analysis**: Explain why the crash occurred in 2-3 sentences.
2. **Impact Assessment**: What risks does this pose in production?
3. **Recommended Fix**: Provide the exact code diff or corrected code snippet to prevent this failure (e.g. debouncing, disabling button, idempotency lock).
"""

        # Check if an API key is available in environment
        has_api_key = any(k in os.environ for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"])

        if not has_api_key:
            return {
                "run_id": target_dir.name,
                "incident": incident_data,
                "diagnosis": (
                    "⚠ **No LLM API key detected** (GEMINI_API_KEY, OPENAI_API_KEY, etc.).\n\n"
                    + self._local_diagnosis(incident_data, source_file)
                    + "\n\n_Tip: Set `GEMINI_API_KEY` in your environment to enable real-time dynamic AI diagnosis._"
                ),
            }

        models_to_try = [
            model or resolve_model(),
            "gemini/gemini-flash-lite-latest",
            "gemini/gemini-2.5-flash",
            "gemini/gemini-3.5-flash-lite",
        ]

        last_error = "Unknown error"
        for m in models_to_try:
            try:
                # Query the model using LiteLLM
                response = litellm.completion(
                    model=m,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=25,
                    num_retries=1,
                )
                analysis = response.choices[0].message.content
                return {
                    "run_id": target_dir.name,
                    "incident": incident_data,
                    "diagnosis": analysis,
                }
            except Exception as e:
                last_error = str(e)
                continue

        # If all cloud models are unavailable (e.g. 503 spikes), provide deterministic diagnosis
        return {
            "run_id": target_dir.name,
            "incident": incident_data,
            "diagnosis": (
                "⚠ **Cloud AI models unavailable. Activated local diagnosis:**\n\n"
                + self._local_diagnosis(incident_data, source_file)
                + f"\n\n_(Original error: {last_error})_"
            ),
        }

    @staticmethod
    def _local_diagnosis(incident_data: Dict[str, Any], source_file: Optional[Path]) -> str:
        """Builds an offline diagnosis strictly from the evidence stored in the incident."""
        crashes = incident_data.get("crashes") or []
        http_errors = incident_data.get("http_errors") or []
        lines = ["**Local Diagnosis (evidence only, no AI reasoning):**"]
        if crashes:
            lines.append("- **Unhandled errors:** " + "; ".join(crashes[:5]))
        if http_errors:
            lines.append("- **Server failures:** " + "; ".join(http_errors[:5]))
        if not crashes and not http_errors:
            lines.append("- No crash evidence was recorded in this incident.")
        lines.append(f"- **Persona:** {incident_data.get('persona') or 'Passive Observer'}")
        lines.append(
            f"- **Suspected source file:** `{source_file}`" if source_file
            else "- **Suspected source file:** could not be determined."
        )
        lines.append("- **Next step:** run `loki replay` to reproduce it, then inspect the file above around the failing code path.")
        return "\n".join(lines)

    def evaluate_business_rules(
        self,
        report: IncidentReport,
        rules_content: str,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluates plain English business assertions against execution evidence."""
        prompt = f"""You are LOKI's Autonomous Business Logic Verification Engine.
Evaluate the following business assertions against the live application behavior recorded during the test session.

### Defined Business Rules:
{rules_content}

### Execution Evidence:
- Target URL: {report.target_url}
- Emulated Device: {report.device_name or 'Desktop Standard'} ({report.orientation})
- Mobile Responsive Layout Anomalies: {json.dumps(report.layout_issues, indent=2)}
- Actions Taken: {json.dumps(report.actions_taken, indent=2)}
- Unhandled Crashes Detected: {len(report.crashes)}
- Crash Details: {json.dumps(report.crashes, indent=2)}
- Final DOM State & Interactive Elements:
{report.dom_snapshot or "No DOM snapshot available."}

### Evaluation Instructions:
For each rule or bullet point in the business rules, evaluate if it PASSED or was VIOLATED based on the evidence.
Respond ONLY with a valid JSON array of objects following this exact schema:
[
  {{
    "rule": "Summary of the business rule",
    "status": "PASSED" or "VIOLATED",
    "observation": "Brief explanation citing specific evidence (e.g. element state, exception count, message text)"
  }}
]
"""
        has_api_key = any(k in os.environ for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"])
        if not has_api_key:
            return [{
                "rule": "Business Rules Evaluation",
                "status": "SKIPPED",
                "observation": "No API key configured in environment."
            }]

        models_to_try = [model or resolve_model(), "gemini/gemini-flash-latest"]

        last_error = "Unknown error"
        for m in models_to_try:
            for attempt in range(2):
                try:
                    response = litellm.completion(
                        model=m,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                    )
                    raw = response.choices[0].message.content.strip()
                    # Clean possible markdown formatting
                    if raw.startswith("```"):
                        lines = raw.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        raw = "\n".join(lines).strip()
                    return json.loads(raw)
                except Exception as e:
                    last_error = str(e)
                    time.sleep(1.0)

        return [{
            "rule": "Business Rules Evaluation Error",
            "status": "ERROR",
            "observation": f"AI model evaluation error: {last_error}"
        }]