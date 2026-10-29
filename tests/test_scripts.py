"""Tests for scripts/: CI state, the CI watcher, and the time report. No network: API calls are faked."""
import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ci_state  # noqa: E402

spec = importlib.util.spec_from_file_location("watch_ci", ROOT / "scripts" / "watch-ci.py")
watch_ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch_ci)

GH = {"provider": "github-actions", "repo": "me/app"}
BB = {"provider": "bitbucket", "repo": "team/app"}


def gh_api(runs, statuses=()):
    """Fake GitHub API: check runs as (name, status, conclusion), statuses as (context, state)."""
    def get(url, headers):
        if url.endswith("/status"):
            return {"statuses": [{"context": c, "state": s} for c, s in statuses]}
        return {"check_runs": [{"name": n, "status": st, "conclusion": c} for n, st, c in runs]}
    return get


class CiState(unittest.TestCase):
    def test_github_reduces_runs_and_statuses(self):
        state, checks = ci_state.commit_state(GH, "abc", get=gh_api(
            [("tests", "completed", "success"), ("lint", "completed", "skipped")], [("deploy-preview", "success")]))
        self.assertEqual(state, "success")
        self.assertEqual(len(checks), 3)

    def test_failure_beats_pending_beats_success(self):
        get = gh_api([("tests", "in_progress", None), ("lint", "completed", "failure"), ("build", "completed", "success")])
        self.assertEqual(ci_state.commit_state(GH, "abc", get=get)[0], "failure")
        get = gh_api([("tests", "queued", None), ("build", "completed", "success")])
        self.assertEqual(ci_state.commit_state(GH, "abc", get=get)[0], "pending")

    def test_cancelled_and_timed_out_count_as_failure(self):
        for conclusion in ("cancelled", "timed_out", "action_required"):
            with self.subTest(conclusion=conclusion):
                get = gh_api([("tests", "completed", conclusion)])
                self.assertEqual(ci_state.commit_state(GH, "abc", get=get)[0], "failure")

    def test_no_checks_yet_is_none(self):
        self.assertEqual(ci_state.commit_state(GH, "abc", get=gh_api([]))[0], "none")

    def test_bitbucket(self):
        get = lambda url, h: {"values": [{"name": "Pipeline #9", "state": "INPROGRESS"}, {"key": "lint", "state": "SUCCESSFUL"}]}
        self.assertEqual(ci_state.commit_state(BB, "abc", get=get)[0], "pending")
        get = lambda url, h: {"values": [{"name": "Pipeline #9", "state": "STOPPED"}]}
        self.assertEqual(ci_state.commit_state(BB, "abc", get=get)[0], "failure")

    def test_config_errors(self):
        with self.assertRaises(ci_state.ConfigError):
            ci_state.config({"checks": {"ci": {"provider": "none"}}})
        with self.assertRaises(ci_state.ConfigError):
            ci_state.config({}, {"provider": "github-actions"})
        cfg = ci_state.config({"checks": {"ci": {"provider": "bitbucket", "repo": "t/a"}}}, {"repo": "t/b"})
        self.assertEqual((cfg["repo"], cfg["token_env"]), ("t/b", "BITBUCKET_TOKEN"))


class WatchCi(unittest.TestCase):
    def run_watch(self, argv, get, polls=None):
        out, calls = io.StringIO(), []
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = watch_ci.main(argv + ["--provider", "github-actions", "--repo", "me/app", "--workspace", "/nonexistent"],
                                 get=get, sleep=lambda s: calls.append(s), clock=polls or (lambda: 0))
        return code, out.getvalue(), len(calls)

    def test_waits_until_every_sha_is_done(self):
        rounds = iter([
            [("tests", "queued", None)],                              # sha1 poll 1
            [("tests", "completed", "success")],                      # sha2 poll 1
            [("tests", "completed", "success")],                      # sha1 poll 2
            [("tests", "completed", "success")],                      # sha2 poll 2
        ])
        state = {}

        def get(url, headers):
            if url.endswith("/status"):
                return {"statuses": []}
            state["runs"] = next(rounds)
            return {"check_runs": [{"name": n, "status": s, "conclusion": c} for n, s, c in state["runs"]]}
        code, out, sleeps = self.run_watch(["sha1aaaaaaaa", "sha2bbbbbbbb"], get)
        self.assertEqual((code, sleeps), (0, 1))
        self.assertIn("sha1aaaaaa pending", out.splitlines()[0])

    def test_failure_exit_code_names_the_check(self):
        code, out, _ = self.run_watch(["abc"], gh_api([("e2e", "completed", "failure"), ("unit", "completed", "success")]))
        self.assertEqual(code, 1)
        self.assertIn("failed: e2e", out)

    def test_network_errors_keep_watching_until_timeout(self):
        def get(url, headers):
            raise OSError("down")
        ticks = iter([0, 0, 10_000])
        code, out, sleeps = self.run_watch(["abc", "--timeout-min", "1"], get, polls=lambda: next(ticks))
        self.assertEqual(code, 2)
        self.assertIn("lookup error: OSError", out)
        self.assertIn("TIMEOUT", out)

    def test_missing_config_is_exit_3(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(watch_ci.main(["abc", "--workspace", "/nonexistent"]), 3)


class TimeReport(unittest.TestCase):
    def test_waits_are_subtracted_from_active(self):
        with tempfile.TemporaryDirectory() as ws:
            (pathlib.Path(ws) / "timelog").mkdir()
            rows = [("09:00", "start"), ("09:30", "wait_start"), ("10:30", "wait_end"), ("11:00", "handoff")]
            (pathlib.Path(ws) / "timelog" / "2026-10-01.jsonl").write_text("".join(
                json.dumps({"ts": f"2026-10-01T{t}:00+07:00", "event": e, "item": "JOB-1", "client": "acme"}) + "\n"
                for t, e in rows))
            out = subprocess.run([sys.executable, str(ROOT / "scripts" / "time-report.py"), "--since", "2026-10-01",
                                  "--workspace", ws], capture_output=True, text=True, check=True).stdout
        line = next(line for line in out.splitlines() if line.startswith("JOB-1"))
        self.assertEqual(line.split()[2:5], ["1h00m", "1h00m", "2h00m"])  # active, wait, span


if __name__ == "__main__":
    unittest.main()
