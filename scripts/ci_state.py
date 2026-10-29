"""CI state for a commit, from GitHub Actions or Bitbucket Pipelines. Standard library only.

Used by watch-ci.py (wait for CI) and the guards hook (no handoff on a red head commit).

  cfg = config(profile, overrides)        # {provider, repo, token_env, user_env}
  overall, checks = commit_state(cfg, sha)

Every check is reduced to one of: pending | success | failure.
overall is "none" when the commit has no checks yet, otherwise failure > pending > success.
"""
import base64
import json
import os
import urllib.request

API = {"github-actions": "https://api.github.com", "bitbucket": "https://api.bitbucket.org/2.0"}
DEFAULT_TOKEN_ENV = {"github-actions": "GITHUB_TOKEN", "bitbucket": "BITBUCKET_TOKEN"}

GH_DONE_OK = {"success", "neutral", "skipped"}
GH_STATUS = {"success": "success", "pending": "pending", "failure": "failure", "error": "failure"}
BB_STATE = {"SUCCESSFUL": "success", "INPROGRESS": "pending", "FAILED": "failure", "STOPPED": "failure"}


class ConfigError(Exception):
    pass


def config(profile=None, overrides=None):
    ci = dict(((profile or {}).get("checks") or {}).get("ci") or {})
    ci.update({k: v for k, v in (overrides or {}).items() if v})
    provider = ci.get("provider") or "none"
    if provider not in API:
        raise ConfigError(f"CI provider '{provider}' is not supported (use github-actions or bitbucket)")
    if not ci.get("repo"):
        raise ConfigError("checks.ci.repo is not set (owner/name on GitHub, workspace/repo on Bitbucket)")
    ci.setdefault("token_env", DEFAULT_TOKEN_ENV[provider])
    return ci


def _headers(cfg):
    token = os.environ.get(cfg.get("token_env") or "", "")
    if not token:
        return {}  # public repos work without one, at a lower rate limit
    user = os.environ.get(cfg.get("user_env") or "", "")
    if user:  # Bitbucket app password / API token with a username
        return {"Authorization": "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode()}
    return {"Authorization": f"Bearer {token}"}


def _get(url, headers, timeout=15):
    req = urllib.request.Request(url, headers=dict(headers, Accept="application/json"))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def github_checks(runs_payload, status_payload):
    """Check runs (Actions) plus legacy commit statuses (other CI posting to GitHub)."""
    checks = []
    for run in runs_payload.get("check_runs", []):
        if run.get("status") != "completed":
            state = "pending"
        else:
            state = "success" if run.get("conclusion") in GH_DONE_OK else "failure"
        checks.append((run.get("name", "?"), state))
    for st in status_payload.get("statuses", []):
        checks.append((st.get("context", "?"), GH_STATUS.get(st.get("state"), "pending")))
    return checks


def bitbucket_checks(statuses_payload):
    return [(v.get("name") or v.get("key") or "?", BB_STATE.get(v.get("state"), "pending"))
            for v in statuses_payload.get("values", [])]


def overall(checks):
    states = {s for _, s in checks}
    if not states:
        return "none"
    for s in ("failure", "pending"):
        if s in states:
            return s
    return "success"


def commit_state(cfg, sha, get=_get):
    """Return (overall, [(check name, state)]). Network errors propagate; callers decide whether to block."""
    base, h = API[cfg["provider"]], _headers(cfg)
    if cfg["provider"] == "github-actions":
        runs = get(f"{base}/repos/{cfg['repo']}/commits/{sha}/check-runs?per_page=100", h)
        status = get(f"{base}/repos/{cfg['repo']}/commits/{sha}/status", h)
        checks = github_checks(runs, status)
    else:
        checks = bitbucket_checks(get(f"{base}/repositories/{cfg['repo']}/commit/{sha}/statuses?pagelen=100", h))
    return overall(checks), checks
