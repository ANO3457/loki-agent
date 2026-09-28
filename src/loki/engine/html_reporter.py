import html
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class HTMLReporter:
    """Generates standalone, responsive HTML test reports with embedded replay video and AI scorecards."""

    @classmethod
    def generate(cls, data: Dict[str, Any], output_file: Path) -> Path:
        """Renders incident or test session data into an HTML dashboard."""
        run_id = html.escape(str(data.get("run_id", "LOKI Test Run")))
        target_url = html.escape(str(data.get("target_url", "")))
        timestamp = html.escape(str(data.get("timestamp", "")))
        duration = f"{data.get('duration_seconds', 0):.2f}s"
        persona = html.escape(str(data.get("persona", "Unguided Chaos")))
        video_file = data.get("video_file")
        crashes = data.get("crashes", [])
        http_errors = data.get("http_errors", [])
        actions = data.get("actions_taken", [])
        rules_evals = data.get("rules_evaluations", [])

        # Verdict calculation
        has_violations = any(r.get("status") == "VIOLATED" for r in rules_evals)
        has_crashes = len(crashes) > 0 or len(http_errors) > 0
        
        if has_crashes or has_violations:
            verdict_badge = '<span class="badge badge-danger">FAIL / ISSUES DETECTED</span>'
            verdict_border = "border-danger"
        else:
            verdict_badge = '<span class="badge badge-success">ALL CHECKS PASSED</span>'
            verdict_border = "border-success"

        # Rules table rows
        rules_rows = ""
        if rules_evals:
            for r in rules_evals:
                st = r.get("status", "UNKNOWN").upper()
                if st == "PASSED":
                    badge = '<span class="badge badge-success">✔ PASSED</span>'
                elif st == "VIOLATED":
                    badge = '<span class="badge badge-danger">❌ VIOLATED</span>'
                else:
                    badge = f'<span class="badge badge-warning">{html.escape(st)}</span>'
                
                rule_text = html.escape(r.get("rule", ""))
                obs_text = html.escape(r.get("observation", ""))
                rules_rows += f"""
                <tr>
                    <td style="font-weight: 500;">{rule_text}</td>
                    <td style="text-align: center;">{badge}</td>
                    <td style="color: #8b949e; font-size: 13px;">{obs_text}</td>
                </tr>
                """
        else:
            rules_rows = '<tr><td colspan="3" style="text-align: center; color: #8b949e; padding: 20px;">No business rules evaluated for this run.</td></tr>'

        # Actions list
        actions_html = ""
        for act in actions:
            actions_html += f'<li class="timeline-item"><span class="bullet"></span><span class="action-text">{html.escape(act)}</span></li>\n'

        # Crashes list
        crashes_html = ""
        if crashes or http_errors:
            for c in crashes:
                crashes_html += f'<div class="error-item"><strong>Unhandled Exception:</strong> {html.escape(str(c))}</div>'
            for h in http_errors:
                crashes_html += f'<div class="error-item"><strong>HTTP Failure:</strong> {html.escape(str(h))}</div>'
        else:
            crashes_html = '<div class="no-errors">🛡️ Zero unhandled crashes or HTTP failures detected.</div>'

        # Video section
        video_html = ""
        if video_file and (output_file.parent / video_file).exists():
            video_html = f"""
            <div class="card">
                <h2>📹 Incident Session Replay</h2>
                <div class="video-container">
                    <video controls autoplay muted loop>
                        <source src="{html.escape(video_file)}" type="video/webm">
                        Your browser does not support the video tag.
                    </video>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LOKI Report — {run_id}</title>
    <style>
        :root {{
            --bg-main: #0d1117;
            --bg-card: #161b22;
            --border-color: #30363d;
            --text-main: #c9d1d9;
            --text-heading: #f0f6fc;
            --text-dim: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-yellow: #d29922;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 30px 20px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 1100px;
            width: 100%;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 28px;
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .logo-icon {{
            background: linear-gradient(135deg, #f85149, #a371f7);
            color: white;
            font-weight: 900;
            font-size: 20px;
            padding: 8px 14px;
            border-radius: 8px;
        }}
        .logo-title h1 {{
            font-size: 22px;
            color: var(--text-heading);
            font-weight: 700;
        }}
        .logo-title p {{
            font-size: 13px;
            color: var(--text-dim);
        }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .badge-success {{
            background-color: rgba(63, 185, 80, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(63, 185, 80, 0.4);
        }}
        .badge-danger {{
            background-color: rgba(248, 81, 73, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(248, 81, 73, 0.4);
        }}
        .badge-warning {{
            background-color: rgba(210, 153, 34, 0.15);
            color: var(--accent-yellow);
            border: 1px solid rgba(210, 153, 34, 0.4);
        }}
        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px 20px;
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-dim);
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .stat-value {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-heading);
        }}
        .card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .card h2 {{
            font-size: 18px;
            color: var(--text-heading);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            color: var(--text-dim);
            font-size: 12px;
            text-transform: uppercase;
        }}
        .video-container video {{
            width: 100%;
            max-height: 480px;
            border-radius: 6px;
            background-color: #000;
            border: 1px solid var(--border-color);
        }}
        .timeline {{
            list-style: none;
            padding-left: 10px;
        }}
        .timeline-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 8px 0;
            border-left: 2px solid var(--border-color);
            padding-left: 16px;
            position: relative;
        }}
        .bullet {{
            position: absolute;
            left: -5px;
            top: 14px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-blue);
        }}
        .action-text {{
            font-size: 13px;
            color: var(--text-main);
            font-family: monospace;
        }}
        .error-item {{
            background-color: rgba(248, 81, 73, 0.1);
            border-left: 4px solid var(--accent-red);
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 4px;
            font-size: 13px;
            font-family: monospace;
            color: #ff7b72;
        }}
        .no-errors {{
            color: var(--accent-green);
            font-size: 14px;
            padding: 10px 0;
        }}
        footer {{
            text-align: center;
            color: var(--text-dim);
            font-size: 12px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">⚡ LOKI</div>
                <div class="logo-title">
                    <h1>Quality & Chaos Report</h1>
                    <p>{run_id} • {timestamp}</p>
                </div>
            </div>
            <div>
                {verdict_badge}
            </div>
        </header>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">Target URL</div>
                <div class="stat-value" style="font-size: 14px; word-break: break-all;">{target_url}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Persona</div>
                <div class="stat-value">{persona}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Session Duration</div>
                <div class="stat-value">{duration}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Actions Executed</div>
                <div class="stat-value">{len(actions)}</div>
            </div>
        </div>

        {video_html}

        <div class="card">
            <h2>📋 Business Rules Verification Scorecard</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 35%;">Business Assertion</th>
                        <th style="width: 15%; text-align: center;">Status</th>
                        <th style="width: 50%;">AI Observation / Evidence</th>
                    </tr>
                </thead>
                <tbody>
                    {rules_rows}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>💥 Crash & Exception Sniffer</h2>
            {crashes_html}
        </div>

        <div class="card">
            <h2>📜 Chronological Actions Timeline ({len(actions)})</h2>
            <ul class="timeline">
                {actions_html}
            </ul>
        </div>

        <footer>
            Generated automatically by <strong>LOKI Agent</strong> — Autonomous AI Chaos Testing & Quality Platform.
        </footer>
    </div>
</body>
</html>
"""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_file
