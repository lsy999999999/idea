"""A separate, closed-material CLI adapter; never changes the existing runtime."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import tomllib


DISABLED = (
    "shell_tool", "unified_exec", "code_mode", "code_mode_host", "apps", "plugins",
    "remote_plugin", "skill_search", "browser_use", "computer_use", "in_app_browser",
    "in_app_local_automation", "multi_agent", "multi_agent_v2", "view_image", "hooks",
    "memories", "shell_snapshot", "workspace_dependencies", "image_generation",
    "artifact", "goals", "sleep_tool", "tool_suggest",
)


def parse_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Correct only a mismatched closing delimiter OUTSIDE strings. No content edits.
        chars, stack, repairs = list(text), [], []
        quoted = escaped = False
        for i, char in enumerate(chars):
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                stack.append(char)
            elif char in "]}":
                if not stack:
                    raise ValueError("Unrepairable JSON closing delimiter")
                expected = "]" if stack.pop() == "[" else "}"
                if char != expected:
                    repairs.append({"offset": i, "before": char, "after": expected})
                    chars[i] = expected
        result = json.loads("".join(chars))
        if repairs:
            result["controller_syntax_repairs"] = repairs
        return result


def provider_args():
    # Read only service configuration, never authentication files or credential fields.
    config_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    config = tomllib.loads((config_home / "config.toml").read_text())
    name = config.get("model_provider", "openai")
    if name == "openai":
        return []
    provider = config["model_providers"][name]
    args = ["-c", "model_provider=" + json.dumps(name)]
    for field in ("name", "base_url", "wire_api", "requires_openai_auth", "env_key"):
        if field in provider:
            args += ["-c", f"model_providers.{name}.{field}=" + json.dumps(provider[field])]
    return args


def invoke(prompt, attempt, timeout=180):
    """Only the supplied text is scientific input. Audit all emitted tool events."""
    attempt = Path(attempt).resolve()
    attempt.mkdir(parents=True, exist_ok=False)
    (attempt / "prompt.txt").write_text(prompt)
    # No inherited host tool bridge, thread, or role context. Authentication remains CLI-owned.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CODEX_") or k == "CODEX_HOME"}
    with tempfile.TemporaryDirectory(prefix="closed-inquiry-") as cwd:
        argv = ["codex", "--no-daemon", "exec", "--ignore-user-config", "--ignore-rules",
                "--ephemeral", "--skip-git-repo-check", "--model", "gpt-6-luna",
                "--sandbox", "read-only", "-C", cwd, "-c", 'model_reasoning_effort="low"',
                "-c", "project_doc_max_bytes=0", "-c", 'web_search="disabled"',
                *provider_args()]
        for feature in DISABLED:
            argv += ["--disable", feature]
        argv += ["--json", "--output-last-message", str(attempt / "final.txt"), "-"]
        (attempt / "command.json").write_text(json.dumps(argv, indent=2))
        with (attempt / "events.jsonl").open("x") as out, (attempt / "stderr.log").open("x") as err:
            p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                 stdout=out, stderr=err, text=True, start_new_session=True)
            try:
                p.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                raise RuntimeError("CLI timed out; attempt retained")
    events = [json.loads(line) for line in (attempt / "events.jsonl").read_text().splitlines()
              if line.strip().startswith("{")]
    # Fail closed if there was any command, search, tool, or other executable action.
    allowed = {"agent_message", "reasoning"}
    def expected_disabled_host(e):
        item = e.get("item", {})
        return (item.get("type") == "error" and item.get("message", "").startswith(
            "Code Mode is unavailable because code-mode host is disabled."))

    actions = [e for e in events if e.get("type", "").startswith("item.")
               and e.get("item", {}).get("type") not in allowed and not expected_disabled_host(e)]
    audit = {"requested_model": "gpt-6-luna", "returncode": p.returncode,
             "unexpected_items": actions, "tool_events": len(actions),
             "disabled_host_notices": sum(expected_disabled_host(e) for e in events),
             "usage": [e["usage"] for e in events if "usage" in e]}
    (attempt / "execution_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    if p.returncode or actions or not (attempt / "final.txt").exists():
        raise RuntimeError("CLI failed or attempted a tool; preserved output is not accepted")
    return parse_response((attempt / "final.txt").read_text())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True)
    args = parser.parse_args()
    result = invoke("No research or tools. Return JSON with available_tools, an exhaustive list "
                    "of names actually offered to you. Do not imagine tools.", args.probe)
    print(json.dumps(result))
