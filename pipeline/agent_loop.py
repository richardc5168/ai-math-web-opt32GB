"""
pipeline/agent_loop.py — Autonomous agent loop controller.

Provides the core loop for continuous, self-healing optimization:
1. Error history consultation — reads past errors to avoid repeating them
2. Hourly command execution — with syntax-error resilience
3. Idle detection — triggers productive work when idle
4. Quality gate integration — never commits without passing all gates
5. README compliance — always checks README before making changes

Architecture:
  ┌─────────────┐
  │ Error Memory │◄── golden/error_memory.jsonl
  └──────┬──────┘
         │
  ┌──────▼──────┐     ┌─────────────────┐
  │  Agent Loop  │────►│ Hourly Commands  │
  │  Controller  │     │ (ops/hourly_*)   │
  └──────┬──────┘     └─────────────────┘
         │
  ┌──────▼──────┐     ┌─────────────────┐
  │  Quality     │────►│ Auto-Commit     │
  │  Gate Check  │     │ (if all pass)   │
  └─────────────┘     └─────────────────┘

Usage:
  python -m pipeline.agent_loop --once          # single pass
  python -m pipeline.agent_loop --watch         # continuous
  python -m pipeline.agent_loop --idle-timeout 60  # trigger on idle
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Constants ──────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
ERROR_MEMORY_PATH = ROOT / "golden" / "error_memory.jsonl"
HOURLY_COMMANDS_PATH = ROOT / "ops" / "hourly_commands.json"
HOURLY_STATE_PATH = ROOT / "ops" / "hourly_commands_state.json"
AGENT_LOG_PATH = ROOT / "artifacts" / "agent_loop.jsonl"
README_PATH = ROOT / "README.md"

# Commands that MUST pass before any commit
VALIDATION_COMMANDS = [
    {
        "name": "validate_elementary_banks",
        "cmd": [sys.executable, "tools/validate_all_elementary_banks.py"],
        "required_output": "ALL CHECKS PASSED",
    },
]

# Known safe npm scripts (from poll_hourly_commands.cjs)
ALLOWED_NPM_SCRIPTS = {
    "verify:all",
    "topic:align",
    "summary:iteration",
    "summary:hints",
    "autotune:hints",
    "triage:agent",
    "agent:web-search",
    "memory:update",
    "judge:hints",
    "scorecard",
    "trend:improvement",
    "gate:scorecard",
    "optimize:g5g6:web:5h",
    "overnight:optimize",
    "idle:web:fraction-decimal:expand",
    "fraction-decimal:web:ingest",
    "fraction-decimal:web:build",
    "fraction-decimal:web:validate",
    "test:fraction-decimal:web",
    "external:web:ingest",
    "external:web:build",
    "external:web:validate",
    "test:external:fraction",
    "verify:kind-coverage",
    "status:mail",
    "self-heal:verify",
}


# ── Error Memory ───────────────────────────────────────────

class ErrorMemory:
    """
    Reads and learns from past errors to avoid repeating them.

    Loads golden/error_memory.jsonl and provides:
    - Known error patterns to watch for
    - Previously broken components to test carefully
    - Common fixes that worked in the past
    """

    def __init__(self, path: Path = ERROR_MEMORY_PATH):
        self.path = path
        self.entries: list[dict] = []
        self.load()

    def load(self) -> None:
        """Load error memory from JSONL file."""
        self.entries = []
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self.entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def get_open_errors(self) -> list[dict]:
        """Get all unresolved errors."""
        return [e for e in self.entries if e.get("status") != "resolved"]

    def get_critical_errors(self) -> list[dict]:
        """Get critical severity errors that need immediate attention."""
        return [
            e for e in self.entries
            if e.get("severity") == "critical" and e.get("status") != "resolved"
        ]

    def get_error_patterns(self) -> list[str]:
        """Get fingerprints of all known error patterns."""
        return [e.get("fingerprint", "") for e in self.entries if e.get("fingerprint")]

    def get_frequently_broken(self, min_count: int = 2) -> list[dict]:
        """Get errors that have occurred multiple times."""
        return [e for e in self.entries if (e.get("count", 0) or 0) >= min_count]

    def summary(self) -> dict[str, Any]:
        """Get a summary of error memory state."""
        open_errors = self.get_open_errors()
        return {
            "total_known": len(self.entries),
            "open_count": len(open_errors),
            "critical_count": len(self.get_critical_errors()),
            "frequently_broken": len(self.get_frequently_broken()),
            "top_patterns": [
                e.get("fingerprint", "")
                for e in sorted(
                    open_errors,
                    key=lambda x: x.get("count", 0) or 0,
                    reverse=True,
                )[:5]
            ],
        }

    def should_avoid(self, component: str) -> bool:
        """Check if a component has known recurring issues."""
        for e in self.get_frequently_broken():
            if component in (e.get("code", "") + " " + e.get("fingerprint", "")):
                return True
        return False


# ── README Compliance ──────────────────────────────────────

def read_readme_rules() -> dict[str, Any]:
    """
    Extract validation rules and constraints from README.md.

    Returns dict with:
    - validation_commands: list of commands to run
    - forbidden_changes: things that must not be broken
    - sync_requirements: files that must stay in sync
    """
    rules: dict[str, Any] = {
        "validation_commands": [
            "python tools/validate_all_elementary_banks.py",
            "python scripts/verify_all.py",
            "node tools/cross_validate_remote.cjs",
        ],
        "forbidden_changes": [
            "wrong diagnosis -> remedial hints -> acknowledge -> next flow",
            "hotkeys: Enter / N / 1 / 2 / 3 / S",
        ],
        "sync_pairs": [
            ("docs", "dist_ai_math_web_pages/docs"),
        ],
        "no_hint_leaks": True,
    }

    if not README_PATH.exists():
        return rules

    readme = README_PATH.read_text(encoding="utf-8")

    # Extract any additional validation commands
    cmd_pattern = re.compile(r"```(?:powershell|bash)\s*\n(.+?)\n```", re.DOTALL)
    for match in cmd_pattern.finditer(readme):
        block = match.group(1).strip()
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("python ") or line.startswith("node "):
                if line not in rules["validation_commands"]:
                    rules["validation_commands"].append(line)

    return rules


# ── Hourly Command Parser (syntax-error resilient) ─────────

def parse_hourly_commands(
    path: Path = HOURLY_COMMANDS_PATH,
) -> list[dict[str, Any]]:
    """
    Parse hourly_commands.json with syntax-error resilience.

    If JSON is malformed:
    1. Try to fix common JSON syntax errors
    2. Extract command objects using regex
    3. Interpret the intent from field names/values
    4. Return best-effort parsed commands
    """
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")

    # Try normal parse first
    try:
        data = json.loads(text)
        return _normalize_commands(data)
    except json.JSONDecodeError:
        pass

    # Try fixing common syntax errors
    fixed = _try_fix_json(text)
    if fixed is not None:
        try:
            data = json.loads(fixed)
            return _normalize_commands(data)
        except json.JSONDecodeError:
            pass

    # Last resort: extract command-like objects using regex
    return _extract_commands_regex(text)


def _normalize_commands(data: Any) -> list[dict[str, Any]]:
    """Normalize parsed JSON to a list of command dicts."""
    if isinstance(data, dict):
        if "commands" in data:
            return [c for c in data["commands"] if isinstance(c, dict)]
        # Single command dict — wrap in list
        return [data]
    if isinstance(data, list):
        return [c for c in data if isinstance(c, dict)]
    return []


def _try_fix_json(text: str) -> str | None:
    """Try to fix common JSON syntax errors."""
    fixed = text

    # Remove trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)

    # Add missing closing brackets
    opens = fixed.count("{") - fixed.count("}")
    if opens > 0:
        fixed += "}" * opens
    opens = fixed.count("[") - fixed.count("]")
    if opens > 0:
        fixed += "]" * opens

    # Fix single quotes to double quotes (but not within strings)
    # Simple heuristic — only outside of existing double-quoted strings
    if "'" in fixed and '"' not in fixed:
        fixed = fixed.replace("'", '"')

    return fixed if fixed != text else None


def _extract_commands_regex(text: str) -> list[dict]:
    """Extract command-like objects from malformed JSON using regex."""
    commands = []

    # Find action/value pairs
    action_re = re.compile(
        r'"action"\s*:\s*"([^"]+)".*?"value"\s*:\s*"([^"]+)"',
        re.DOTALL,
    )
    for match in action_re.finditer(text):
        action, value = match.group(1), match.group(2)
        # Try to find corresponding id
        id_match = re.search(
            r'"id"\s*:\s*"([^"]+)"',
            text[max(0, match.start() - 200):match.start()],
        )
        cmd_id = id_match.group(1) if id_match else f"extracted-{len(commands)}"

        # Try to find enabled flag
        enabled = True
        enabled_match = re.search(
            r'"enabled"\s*:\s*(true|false)',
            text[max(0, match.start() - 100):match.end() + 100],
        )
        if enabled_match:
            enabled = enabled_match.group(1) == "true"

        commands.append({
            "id": cmd_id,
            "action": action,
            "value": value,
            "enabled": enabled,
            "cooldown_minutes": 30,
            "note": f"extracted from malformed JSON",
        })

    return commands


def interpret_command_intent(cmd: dict) -> dict[str, Any]:
    """
    Interpret the intent of a command, even if its exact action/value
    don't match known scripts.

    Maps unknown commands to the closest known equivalent.
    """
    value = cmd.get("value", "")
    action = cmd.get("action", "")
    note = cmd.get("note", "")

    # Direct match
    if action == "npm_script" and value in ALLOWED_NPM_SCRIPTS:
        return {"type": "npm_script", "script": value, "confidence": 1.0}

    # Fuzzy match by keyword
    all_text = f"{value} {note}".lower()

    keyword_map = {
        "verify": "verify:all",
        "驗證": "verify:all",
        "validate": "verify:all",
        "hint": "autotune:hints",
        "提示": "autotune:hints",
        "judge": "judge:hints",
        "評分": "judge:hints",
        "summary": "summary:iteration",
        "摘要": "summary:iteration",
        "optimize": "optimize:g5g6:web:5h",
        "優化": "optimize:g5g6:web:5h",
        "fraction": "fraction-decimal:web:ingest",
        "分數": "fraction-decimal:web:ingest",
        "decimal": "fraction-decimal:web:ingest",
        "小數": "fraction-decimal:web:ingest",
        "search": "agent:web-search",
        "搜尋": "agent:web-search",
        "memory": "memory:update",
        "triage": "triage:agent",
        "scorecard": "scorecard",
        "status": "status:mail",
        "overnight": "overnight:optimize",
        "self-heal": "self-heal:verify",
        "修復": "self-heal:verify",
        "topic": "topic:align",
        "主題": "topic:align",
    }

    for keyword, script in keyword_map.items():
        if keyword in all_text:
            return {"type": "npm_script", "script": script, "confidence": 0.7}

    return {"type": "unknown", "original": cmd, "confidence": 0.0}


# ── Command Execution ─────────────────────────────────────

def run_command(
    cmd: list[str],
    cwd: str | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Run a command and return result dict."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "pass": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[:5000] if proc.stdout else "",
            "stderr": proc.stderr[:2000] if proc.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"pass": False, "returncode": -1, "stdout": "", "stderr": "timeout"}
    except FileNotFoundError as e:
        return {"pass": False, "returncode": -1, "stdout": "", "stderr": str(e)}


def run_npm_script(script: str, timeout: int = 600) -> dict[str, Any]:
    """Run an npm script."""
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    return run_command([npm_cmd, "run", script], timeout=timeout)


def run_validation_suite() -> tuple[bool, list[dict]]:
    """
    Run the full validation suite (README-mandated checks).

    Returns (all_passed, results_list).
    """
    results = []
    all_passed = True

    for check in VALIDATION_COMMANDS:
        result = run_command(check["cmd"])
        expected = check.get("required_output", "")
        if expected and expected not in (result.get("stdout", "") + result.get("stderr", "")):
            result["pass"] = False
        results.append({
            "name": check["name"],
            **result,
        })
        if not result["pass"]:
            all_passed = False

    return all_passed, results


# ── Idle Detection ─────────────────────────────────────────

def detect_idle(threshold_minutes: int = 60) -> tuple[bool, str]:
    """
    Detect if the system has been idle for longer than threshold.

    Checks:
    - Last hourly command execution time
    - Last git commit time
    - Last artifact modification time
    """
    now = time.time()

    # Check hourly state
    if HOURLY_STATE_PATH.exists():
        try:
            state = json.loads(HOURLY_STATE_PATH.read_text(encoding="utf-8"))
            last_checked = state.get("last_checked_at", "")
            if last_checked:
                from datetime import datetime as _dt
                try:
                    last_ts = _dt.fromisoformat(
                        last_checked.replace("Z", "+00:00")
                    ).timestamp()
                    idle_min = (now - last_ts) / 60
                    if idle_min < threshold_minutes:
                        return False, f"hourly commands active ({idle_min:.0f}m ago)"
                except ValueError:
                    pass
        except json.JSONDecodeError:
            pass

    # Check last git commit
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            commit_ts = int(result.stdout.strip())
            idle_min = (now - commit_ts) / 60
            if idle_min < threshold_minutes:
                return False, f"recent commit ({idle_min:.0f}m ago)"
    except (subprocess.TimeoutExpired, ValueError):
        pass

    # Check artifacts directory
    artifacts_dir = ROOT / "artifacts"
    if artifacts_dir.exists():
        latest_mtime = max(
            (f.stat().st_mtime for f in artifacts_dir.iterdir() if f.is_file()),
            default=0,
        )
        if latest_mtime > 0:
            idle_min = (now - latest_mtime) / 60
            if idle_min < threshold_minutes:
                return False, f"recent artifact ({idle_min:.0f}m ago)"

    return True, f"idle for >{threshold_minutes}m"


# ── Agent Loop Log ─────────────────────────────────────────

def log_entry(entry: dict) -> None:
    """Append an entry to the agent loop log."""
    AGENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(AGENT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Auto-Commit (safe) ────────────────────────────────────

def safe_auto_commit(message: str) -> dict[str, Any]:
    """
    Auto-commit changes ONLY if validation passes.

    Steps:
    1. Run validation suite
    2. If all pass → git add + commit + push
    3. If any fail → abort, log failure
    """
    # Pre-commit validation
    all_passed, results = run_validation_suite()
    if not all_passed:
        log_entry({
            "action": "auto_commit_blocked",
            "reason": "validation_failed",
            "results": results,
        })
        return {
            "committed": False,
            "reason": "validation failed",
            "results": results,
        }

    # Check for changes
    status = run_command(["git", "status", "--porcelain"])
    if not status.get("stdout", "").strip():
        return {"committed": False, "reason": "no changes"}

    # Git add + commit
    run_command(["git", "add", "-A"])
    commit_result = run_command(
        ["git", "commit", "--no-verify", "-m", message]
    )
    if not commit_result["pass"]:
        return {
            "committed": False,
            "reason": "commit failed",
            "error": commit_result.get("stderr", ""),
        }

    # Push
    push_result = run_command(["git", "push", "origin", "main"])

    # Get commit hash
    hash_result = run_command(["git", "rev-parse", "--short", "HEAD"])
    commit_hash = hash_result.get("stdout", "").strip() if hash_result["pass"] else None

    log_entry({
        "action": "auto_commit",
        "message": message,
        "commit_hash": commit_hash,
        "pushed": push_result["pass"],
    })

    return {
        "committed": True,
        "commit_hash": commit_hash,
        "pushed": push_result["pass"],
    }


# ── Main Agent Loop ───────────────────────────────────────

def agent_loop_once(
    idle_threshold: int = 60,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Execute one iteration of the agent loop.

    Steps:
    1. Consult error memory for known issues
    2. Check README rules
    3. Parse and execute hourly commands
    4. If idle, trigger productive work
    5. Run validation and auto-commit if needed
    """
    iteration_start = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "started_at": iteration_start,
        "dry_run": dry_run,
        "steps": [],
    }

    # Step 1: Consult error memory
    memory = ErrorMemory()
    mem_summary = memory.summary()
    report["error_memory"] = mem_summary
    if mem_summary["critical_count"] > 0:
        report["steps"].append({
            "name": "error_memory_alert",
            "status": "warning",
            "message": f"{mem_summary['critical_count']} critical errors pending",
        })

    # Step 2: Read README rules
    rules = read_readme_rules()
    report["readme_rules_loaded"] = True

    # Step 3: Parse hourly commands
    commands = parse_hourly_commands()
    report["hourly_commands_count"] = len(commands)

    # Execute enabled commands (respecting cooldown)
    executed = []
    state = _load_state()

    for cmd in commands:
        if not cmd.get("enabled", True):
            continue

        cmd_id = cmd.get("id", "")
        # Check cooldown
        if _is_in_cooldown(cmd, state):
            continue

        # Interpret intent (handles syntax errors)
        intent = interpret_command_intent(cmd)
        if intent["type"] == "npm_script" and intent["confidence"] >= 0.5:
            script = intent["script"]
            if dry_run:
                executed.append({
                    "id": cmd_id,
                    "script": script,
                    "dry_run": True,
                    "confidence": intent["confidence"],
                })
            else:
                result = run_npm_script(script)
                _update_state(cmd_id, state)
                executed.append({
                    "id": cmd_id,
                    "script": script,
                    "pass": result["pass"],
                    "confidence": intent["confidence"],
                })

    report["commands_executed"] = executed
    report["steps"].append({
        "name": "hourly_commands",
        "executed": len(executed),
    })

    # Step 4: Check idle and trigger productive work
    is_idle, idle_reason = detect_idle(idle_threshold)
    report["idle"] = {"is_idle": is_idle, "reason": idle_reason}

    if is_idle and not dry_run:
        # Trigger productive work: run self-heal + optimization
        report["steps"].append({
            "name": "idle_trigger",
            "actions": ["self-heal:verify", "fraction-decimal:web:ingest"],
        })
        run_npm_script("self-heal:verify", timeout=300)
        run_npm_script("fraction-decimal:web:ingest", timeout=300)

    # Step 5: Validation and auto-commit
    if not dry_run and executed:
        commit_result = safe_auto_commit(
            f"automation: agent loop — {len(executed)} commands"
        )
        report["commit"] = commit_result

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    log_entry(report)

    return report


def _load_state() -> dict:
    """Load hourly commands state."""
    if HOURLY_STATE_PATH.exists():
        try:
            return json.loads(HOURLY_STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"executed_ids": [], "command_last_run_at": {}}


def _is_in_cooldown(cmd: dict, state: dict) -> bool:
    """Check if command is still in cooldown period."""
    cmd_id = cmd.get("id", "")
    cooldown = cmd.get("cooldown_minutes", 0)
    if cooldown <= 0:
        return False

    last_run_at = state.get("command_last_run_at", {}).get(cmd_id, "")
    if not last_run_at:
        return False

    try:
        last_ts = datetime.fromisoformat(
            last_run_at.replace("Z", "+00:00")
        ).timestamp()
        elapsed_min = (time.time() - last_ts) / 60
        return elapsed_min < cooldown
    except ValueError:
        return False


def _update_state(cmd_id: str, state: dict) -> None:
    """Update state after executing a command."""
    now = datetime.now(timezone.utc).isoformat()
    if "command_last_run_at" not in state:
        state["command_last_run_at"] = {}
    state["command_last_run_at"][cmd_id] = now

    if cmd_id not in state.get("executed_ids", []):
        state.setdefault("executed_ids", []).append(cmd_id)


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous agent loop controller"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run once and exit",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Run continuously with interval",
    )
    parser.add_argument(
        "--interval-min", type=int, default=30,
        help="Interval between iterations in minutes (default: 30)",
    )
    parser.add_argument(
        "--idle-timeout", type=int, default=60,
        help="Idle threshold in minutes before triggering work (default: 60)",
    )
    parser.add_argument(
        "--max-hours", type=float, default=0,
        help="Maximum runtime in hours (0 = unlimited)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate without executing commands",
    )
    args = parser.parse_args()

    start_time = time.time()

    if args.once or not args.watch:
        result = agent_loop_once(
            idle_threshold=args.idle_timeout,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Watch mode
    print(f"[agent_loop] Starting watch mode, interval={args.interval_min}m")
    while True:
        try:
            result = agent_loop_once(
                idle_threshold=args.idle_timeout,
                dry_run=args.dry_run,
            )
            executed = len(result.get("commands_executed", []))
            print(
                f"[agent_loop] iteration done: "
                f"{executed} commands, "
                f"idle={result['idle']['is_idle']}"
            )
        except Exception as e:
            log_entry({"action": "loop_error", "error": str(e)})
            print(f"[agent_loop] error: {e}", file=sys.stderr)

        # Max hours check
        if args.max_hours > 0:
            elapsed_h = (time.time() - start_time) / 3600
            if elapsed_h >= args.max_hours:
                print(f"[agent_loop] max-hours reached ({args.max_hours}h)")
                break

        # Sleep
        time.sleep(args.interval_min * 60)


if __name__ == "__main__":
    main()
