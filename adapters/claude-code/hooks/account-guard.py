#!/usr/bin/env python3
"""PreToolUse (Playwright MCP): on the local app, agents log in ONLY with test accounts.

Real accounts lock after a few failed logins, and a test password tried on a real account is exactly that.
With profile test_data.login_prefix set (e.g. "demo-"), this blocks a browser call that puts any other
login identifier into a login field:
  - browser_fill_form: a field whose name looks like a login field (user / username / login / email)
  - browser_type: an element description that looks like a login field
  - browser_run_code_unsafe / browser_evaluate: code that touches a login or password field and contains
    an email that doesn't start with the prefix

Ordinary form fields (a contact email on a form) are not touched: the field must look like a login field.

Only while the browser is on the LOCAL app (environments.local.url, localhost, 127.0.0.1): shared
environments name their own accounts. Each navigation (and any page.goto in run-code) records the host in
<workspace>/.agent-team/browser-host. No host recorded yet = allow. Off when login_prefix is unset.
Fail-open on malformed input.
"""
import json
import re
import sys
from urllib.parse import urlparse

from _common import profile, read_input, workspace

GOTO = re.compile(r"\.goto\(\s*['\"`]([^'\"`]+)", re.I)
LOGIN_FIELD = re.compile(r"\b(user(?:name)?|login(?:\s*id)?|e-?mail(?:\s*address)?)\b", re.I)
LOGIN_CODE = re.compile(r"(#?username|['\"]password['\"]|type=['\"]?password|getByLabel\(\s*['\"](?:user|e-?mail|login))", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def state_file():
    return workspace() / ".agent-team" / "browser-host"


def local_hosts(prof):
    hosts = {"localhost", "127.0.0.1"}
    url = ((prof.get("environments") or {}).get("local") or {}).get("url") or ""
    if urlparse(url).hostname:
        hosts.add(urlparse(url).hostname.lower())
    return hosts


def record_host(url):
    host = (urlparse(url).hostname or "").lower()
    if host:
        try:
            state_file().parent.mkdir(parents=True, exist_ok=True)
            state_file().write_text(host)
        except OSError:
            pass


def on_local(prof):
    try:
        return state_file().read_text().strip() in local_hosts(prof)
    except OSError:
        return False


def deny(identifier, prefix):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"Login with '{identifier}' blocked: on the local app agents log in only with test accounts "
            f"('{prefix}…'). Use or create one; never try a real account (agent-team account-guard.py).")}}))
    sys.exit(0)


def check_value(label, value, prefix):
    if not isinstance(value, str) or not value.strip() or "password" in (label or "").lower():
        return
    if LOGIN_FIELD.search(label or "") and not value.strip().lower().startswith(prefix):
        deny(value.strip(), prefix)


def main():
    d = read_input()
    tool, ti = d.get("tool_name") or "", d.get("tool_input") or {}
    prof = profile()
    prefix = str((prof.get("test_data") or {}).get("login_prefix") or "").lower()
    if not prefix:
        return
    if tool.endswith("browser_navigate"):
        record_host(ti.get("url") or "")
        return
    code = ti.get("code") or ti.get("function") or ""
    gotos = GOTO.findall(code) if isinstance(code, str) else []
    if gotos:
        record_host(gotos[-1])
    if not on_local(prof):
        return
    if tool.endswith("browser_fill_form"):
        for f in ti.get("fields") or []:
            if (f.get("type") or "").lower() not in ("checkbox", "radio", "combobox", "slider"):
                check_value(f.get("name", ""), f.get("value"), prefix)
    elif tool.endswith("browser_type"):
        check_value(ti.get("element", ""), ti.get("text"), prefix)
    elif tool.endswith(("browser_run_code_unsafe", "browser_evaluate")) and isinstance(code, str) and LOGIN_CODE.search(code):
        for email in EMAIL.findall(code):
            if not email.lower().startswith(prefix):
                deny(email, prefix)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
