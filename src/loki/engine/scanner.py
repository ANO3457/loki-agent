import json
from pathlib import Path
from typing import Dict, List, Any
import yaml

class ProjectScanner:
    """Scans the repository to identify technology stacks, endpoints, and setup LOKI."""
    def __init__(self, project_root: str = "."):
        self.root = Path(project_root)
        self.loki_dir = self.root / ".loki"
    def detect_stack(self) -> Dict[str, Any]:
        """Detects languages, frameworks, and tools present in the current workspace."""
        detected = {
            "languages": [],
            "frameworks_and_tools": [],
            "detected_files": [],
        }
        # Signatures for common programming environments
        stack_signatures = {
            "Python": ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"],
            "Node.js / TypeScript": ["package.json", "tsconfig.json", "yarn.lock"],
            "Rust": ["Cargo.toml"],
            "Go": ["go.mod"],
            "Web / Static HTML": ["index.html"],
        }
        for language, files in stack_signatures.items():
            for filename in files:
                if (self.root / filename).exists():
                    if language not in detected["languages"]:
                        detected["languages"].append(language)
                    detected["detected_files"].append(filename)
        # Detect specific frameworks if package.json exists
        pkg_json = self.root / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for framework in ["react", "vue", "svelte", "next", "express", "playwright"]:
                        if framework in deps:
                            detected["frameworks_and_tools"].append(framework)
            except Exception:
                pass
        return detected
    def initialize(self, default_target_url: str = "http://localhost:8000") -> Dict[str, str]:
        """Creates the .loki configuration directory and baseline project artifacts."""
        self.loki_dir.mkdir(parents=True, exist_ok=True)
        (self.loki_dir / "runs").mkdir(parents=True, exist_ok=True)
        (self.loki_dir / "journeys").mkdir(parents=True, exist_ok=True)
        stack_info = self.detect_stack()
        # 1. Create config.yaml
        config_data = {
            "version": "1.0",
            "target": {
                "default_url": default_target_url,
                "timeout_seconds": 10,
                "headless": True,
            },
            "chaos": {
                "default_persona": "rage-clicker",
                "click_burst_count": 5,
            },
            "ai": {
                "provider": "gemini",
                "model": "gemini-2.5-flash",
            },
        }
        config_path = self.loki_dir / "config.yaml"
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        # 2. Create rules.md for human-editable business rules
        rules_path = self.loki_dir / "rules.md"
        if not rules_path.exists():
            rules_content = """# LOKI Business Rules & Assertions
Define the business expectations and rules that LOKI should assert when attacking your app.
LOKI evaluates these criteria during stress testing and exploratory sessions.
## Critical Business Assertions
- Action buttons must disable upon click to prevent concurrent double-submissions.
- Unhandled JavaScript exceptions in the browser console are classified as critical failures.
- Forms must display contextual error banners rather than blank pages or unstyled crash screens.
- Financial transactions (payments, transfers) must have deterministic server idempotency locks.
"""
            with open(rules_path, "w", encoding="utf-8") as f:
                f.write(rules_content)
        # 3. Create knowledge.json containing detected architecture DNA
        knowledge_data = {
            "stack": stack_info,
            "project_name": self.root.resolve().name,
            "initialized_at": True,
        }
        knowledge_path = self.loki_dir / "knowledge.json"
        with open(knowledge_path, "w", encoding="utf-8") as f:
            json.dump(knowledge_data, f, indent=2)
        return {
            "config": str(config_path),
            "rules": str(rules_path),
            "knowledge": str(knowledge_path),
        }