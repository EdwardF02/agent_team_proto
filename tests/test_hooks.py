"""Hook tests: each hook gets Claude Code's JSON on stdin, exactly as it would in a session.

  python3 -m unittest discover tests
"""
import contextlib
import importlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "adapters" / "claude-code" / "hooks"
sys.path.insert(0, str(HOOKS))

PROFILE = """
profile: test
work_items: {connector: jira, id_pattern: 'ABC-\\d+'}
statuses: {in_review: '41'}
gates: {merge: on}
test_data: {prefix: demo-, login_prefix: demo-, never: [change existing passwords]}
environments: {local: {url: 'http://myapp.test:8080'}}
checks: {ci: {provider: github-actions, repo: me/app}}
"""


class Workspace:
    """A throwaway workspace with a profile; hooks find it through CLAUDE_PROJECT_DIR."""

    def __init__(self, profile=PROFILE):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name)
        self.cleanup = self.tmp.cleanup
        (self.path / "profile").mkdir()
        (self.path / "profile" / "profile.yaml").write_text(profile)

    def run(self, hook, payload):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.path))
        out = subprocess.run([sys.executable, str(HOOKS / hook)], input=json.dumps(payload),
                             capture_output=True, text=True, env=env, timeout=30)
        return json.loads(out.stdout) if out.stdout.strip() else None


def denied(result):
    return bool(result) and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


class DenyHookBypass(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def test_blocks_bypasses(self):
        for cmd in ["git commit --no-verify -m x", "git commit -n -m x", "cd app && git commit -m 'x' -n",
                    "git push --no-verify", "git -c core.hooksPath=/dev/null commit -m x", "HUSKY=0 git commit -m x"]:
            with self.subTest(cmd=cmd):
                self.assertTrue(denied(self.ws.run("deny-hook-bypass.py", bash(cmd))))

    def test_allows_normal_git(self):
        for cmd in ["git commit -m 'fix -n handling'", "git push -n origin main", "git commit -m x",
                    "grep -n verify file.txt", "git log -n 5"]:
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.ws.run("deny-hook-bypass.py", bash(cmd)))


class Guards(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def test_blocks_password_change_through_a_console(self):
        for cmd in ["php artisan tinker --execute=\"User::find(1)->update(['password'=>Hash::make('x')])\"",
                    "mysql app -e \"UPDATE users SET password='x' WHERE id=1\"",
                    "docker exec web python manage.py shell -c 'u.set_password(\"x\")'"]:
            with self.subTest(cmd=cmd):
                self.assertTrue(denied(self.ws.run("guards.py", bash(cmd))))

    def test_mentioning_passwords_is_fine(self):
        for cmd in ["grep -rn 'Hash::make' app/", "echo 'UPDATE users SET password' >> notes.md",
                    "mysql app -e 'SELECT id FROM users'"]:
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.ws.run("guards.py", bash(cmd)))

    def test_quoted_pipes_stay_in_one_segment(self):
        import guards
        self.assertEqual(guards.segments("grep 'a|b' f && echo ok"), ["grep 'a|b' f", "echo ok"])
        self.assertIn("mysql -e x", guards.segments("bash -c 'cd /tmp; mysql -e x'"))

    def test_merge_is_an_owner_gate(self):
        self.assertTrue(denied(self.ws.run("guards.py", bash("gh pr merge 12 --squash"))))
        self.assertTrue(denied(self.ws.run("guards.py", bash(
            "curl -X POST https://api.bitbucket.org/2.0/repositories/w/r/pullrequests/7/merge"))))
        self.assertTrue(denied(self.ws.run("guards.py", {"tool_name": "mcp__bitbucket__merge_pull_request", "tool_input": {}})))

    def test_merge_allowed_when_gate_off(self):
        ws = Workspace(PROFILE.replace("merge: on", "merge: off"))
        self.addCleanup(ws.cleanup)
        self.assertIsNone(ws.run("guards.py", bash("gh pr merge 12 --squash")))


class HandoffGate(unittest.TestCase):
    """Moving an item to in_review is blocked unless its branch head is green. CI is faked; git is real."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = pathlib.Path(self.tmp.name)
        git = lambda *a, cwd=t: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
        git("init", "-q", "--bare", "origin.git")
        git("init", "-q", "app")
        app = t / "app"
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x", cwd=app)
        git("remote", "add", "origin", str(t / "origin.git"), cwd=app)
        git("push", "-q", "origin", "HEAD:refs/heads/ABC-12-fix-login", cwd=app)
        self.sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=app, capture_output=True, text=True).stdout.strip()
        self.guards = importlib.import_module("guards")
        self.prof = {"repos": [{"name": "app", "path": str(app)}], "statuses": {"in_review": "41"},
                     "checks": {"ci": {"provider": "github-actions", "repo": "me/app"}}}

    def verdict(self, ci_state, item="ABC-12"):
        self.guards.commit_state = lambda cfg, sha: ci_state(sha)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            self.guards.check_handoff(item, self.prof)
        return json.loads(out.getvalue())["hookSpecificOutput"]

    def test_red_head_blocks(self):
        v = self.verdict(lambda sha: ("failure", [("tests", "failure"), ("lint", "success")]))
        self.assertEqual(v["permissionDecision"], "deny")
        self.assertIn(self.sha[:10], v["permissionDecisionReason"])
        self.assertIn("tests", v["permissionDecisionReason"])

    def test_pending_head_blocks(self):
        self.assertEqual(self.verdict(lambda sha: ("pending", [("tests", "pending")]))["permissionDecision"], "deny")

    def test_green_head_passes(self):
        self.guards.commit_state = lambda cfg, sha: ("success", [("tests", "success")])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.guards.check_handoff("ABC-12", self.prof)
        self.assertEqual(out.getvalue(), "")

    def test_lookup_failure_warns_not_blocks(self):
        def boom(sha):
            raise OSError("network down")
        v = self.verdict(boom)
        self.assertNotIn("permissionDecision", v)
        self.assertIn("NOT checked", v["additionalContext"])

    def test_item_id_must_match_a_whole_token(self):
        v = self.verdict(lambda sha: ("failure", []), item="ABC-1")  # ABC-12's branch must not count
        self.assertIn("no pushed branch", v["additionalContext"])

    def test_detects_jira_and_github_handoffs(self):
        g = self.guards
        jira = {"issueIdOrKey": "abc-12", "transition": {"id": "41"}}
        self.assertEqual(g.handoff_item("mcp__atlassian__transitionJiraIssue", jira, "", self.prof), "ABC-12")
        self.assertIsNone(g.handoff_item("mcp__atlassian__transitionJiraIssue",
                                         {"issueIdOrKey": "ABC-12", "transition": {"id": "31"}}, "", self.prof))
        gh = dict(self.prof, statuses={"in_review": "in-review"})
        self.assertEqual(g.handoff_item("Bash", {}, "gh issue edit 34 --add-label in-review", gh), "34")
        self.assertIsNone(g.handoff_item("Bash", {}, "gh issue edit 34 --add-label bug", gh))


class AccountGuard(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)

    def go(self, url):
        self.ws.run("account-guard.py", {"tool_name": "mcp__playwright__browser_navigate", "tool_input": {"url": url}})

    def fill(self, name, value):
        return self.ws.run("account-guard.py", {"tool_name": "mcp__playwright__browser_fill_form",
                                                "tool_input": {"fields": [{"name": name, "type": "textbox", "value": value}]}})

    def test_local_app_needs_a_test_account(self):
        self.go("http://myapp.test:8080/login")
        self.assertTrue(denied(self.fill("Email", "real.person@company.com")))
        self.assertIsNone(self.fill("Email", "demo-admin@company.com"))
        self.assertIsNone(self.fill("Password", "whatever"))
        self.assertIsNone(self.fill("Contact phone", "0812345678"))

    def test_run_code_with_a_real_login(self):
        self.go("http://localhost:3000")
        code = "async (page) => { await page.fill('#username', 'boss@company.com'); await page.fill('[type=password]', 'x') }"
        self.assertTrue(denied(self.ws.run("account-guard.py", {"tool_name": "mcp__playwright__browser_run_code_unsafe",
                                                                "tool_input": {"code": code}})))

    def test_shared_environments_are_not_guarded(self):
        self.go("https://staging.example.com/login")
        self.assertIsNone(self.fill("Email", "qa.lead@company.com"))

    def test_off_without_a_prefix(self):
        ws = Workspace(PROFILE.replace("login_prefix: demo-, ", ""))
        self.addCleanup(ws.cleanup)
        ws.run("account-guard.py", {"tool_name": "mcp__playwright__browser_navigate", "tool_input": {"url": "http://localhost"}})
        self.assertIsNone(ws.run("account-guard.py", {"tool_name": "mcp__playwright__browser_type",
                                                      "tool_input": {"element": "Username", "text": "anyone"}}))


class WaitBracket(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)
        self.env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.ws.path))

    def log(self, event, item):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "log-event.py"), event, item,
                        "--workspace", str(self.ws.path)], check=True)

    def events(self):
        rows = []
        for f in (self.ws.path / "timelog").glob("*.jsonl"):
            rows += [json.loads(line) for line in f.read_text().splitlines()]
        return [(r["event"], r["item"]) for r in rows]

    def test_agent_spawn_closes_only_the_briefs_own_wait(self):
        self.log("start", "ABC-1"); self.log("wait_start", "ABC-1")
        self.log("start", "ABC-2"); self.log("wait_start", "ABC-2")
        self.ws.run("wait-bracket.py", {"hook_event_name": "PreToolUse", "tool_name": "Agent",
                                        "tool_input": {"prompt": "Fix ABC-2. Related: ABC-1 touched this too."}})
        self.assertIn(("wait_end", "ABC-2"), self.events())
        self.assertNotIn(("wait_end", "ABC-1"), self.events())

    def test_nothing_open_means_no_nag(self):
        self.log("start", "ABC-1"); self.log("handoff", "ABC-1")
        self.assertIsNone(self.ws.run("wait-bracket.py", {"hook_event_name": "Stop"}))


if __name__ == "__main__":
    unittest.main()
