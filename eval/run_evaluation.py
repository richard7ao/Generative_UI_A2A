"""Evaluation runner for the A2A agent pair.

Thin wrapper around the `a2a-hack` harness (the sibling a2a-hackathon repo).
It invokes the harness via `uv run`, runs a task split (train/test/feedback or
comma-separated task ids) against the locally running agents, then parses the
tau2 results dir and prints a report.

Usage:
    python3 eval/run_evaluation.py --tasks test      # test-set score
    python3 eval/run_evaluation.py --tasks train     # iterate (default)
    python3 eval/run_evaluation.py --smoke-only      # connectivity check
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HARNESS_DIR = REPO_ROOT.parent / "a2a-hackathon"


def _load_dotenv(path: Path) -> Dict[str, str]:
    """Minimal .env reader so the harness subprocess inherits GOOGLE_API_KEY
    etc. Existing environment values win; we never override them."""
    env = dict(os.environ)
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        env.setdefault(key, value)
    return env


class EvaluationRunner:
    """Runs the harness against the agent pair and reports a score."""

    def __init__(
        self,
        personal_url: str = "http://localhost:9001",
        cs_url: str = "http://localhost:9002",
        harness_dir: Path = DEFAULT_HARNESS_DIR,
        output_dir: Path = None,
    ):
        self.personal_url = personal_url
        self.cs_url = cs_url
        self.harness_dir = Path(harness_dir).resolve()
        if not self.harness_dir.exists():
            raise FileNotFoundError(
                f"Harness repo not found at {self.harness_dir}. Clone "
                "a2anet/a2a-hackathon next to this repo or pass --harness-dir."
            )
        # Default to the harness's own results/ dir so `tau2 view` works as
        # documented in the harness README.
        self.output_dir = Path(output_dir) if output_dir else self.harness_dir / "results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.env = _load_dotenv(REPO_ROOT / ".env")

    def _harness(self, args: List[str], timeout: int) -> subprocess.CompletedProcess:
        """Invoke `uv run --directory <harness> a2a-hack <args>`."""
        cmd = ["uv", "run", "--directory", str(self.harness_dir), "a2a-hack", *args]
        print(f"$ {' '.join(cmd)}")
        return subprocess.run(cmd, env=self.env, timeout=timeout)

    def run_smoke_test(self) -> bool:
        """Run the harness smoke test (one task, loud about contextId bugs)."""
        print("Running smoke test...")
        try:
            result = self._harness(
                [
                    "smoke",
                    "--personal-url", self.personal_url,
                    "--cs-url", self.cs_url,
                ],
                timeout=600,
            )
        except Exception as e:  # noqa: BLE001 - surface any harness failure
            print(f"Smoke test error: {e}")
            return False
        ok = result.returncode == 0
        print("Smoke test PASSED" if ok else "Smoke test FAILED")
        return ok

    def run_eval(self, split: str = "train") -> Dict:
        """Run a task split and return parsed metrics."""
        print(f"Running '{split}' evaluation...")
        results_dir = self.output_dir / f"{split}_{int(time.time())}"

        try:
            result = self._harness(
                [
                    "run",
                    "--personal-url", self.personal_url,
                    "--cs-url", self.cs_url,
                    "--tasks", split,
                    "--save-to", str(results_dir),
                    "--auto-resume",
                ],
                timeout=3600,  # 18 test tasks can take a while end to end
            )
        except subprocess.TimeoutExpired:
            return {"error": "Harness run timed out"}

        results_json = results_dir / "results.json"
        if not results_json.exists():
            return {"error": f"No results.json produced (exit {result.returncode})"}

        metrics = self._analyze_results(json.loads(results_json.read_text()))
        metrics["results_dir"] = str(results_dir)
        # exit 2 means leftover INFRASTRUCTURE_ERROR sims; results are still valid
        if result.returncode not in (0, 2):
            metrics["warning"] = f"harness exited {result.returncode}"
        return metrics

    def _analyze_results(self, data: Dict) -> Dict:
        """Analyze a tau2 results.json (uses the simulation_index rewards)."""
        sims = data.get("simulation_index", [])
        rewards = [s.get("reward") for s in sims if s.get("reward") is not None]
        total = len(sims)
        scored = len(rewards)

        mean_reward = sum(rewards) / scored if scored else 0.0
        full_credit = sum(1 for r in rewards if r >= 0.999)
        zero = sum(1 for r in rewards if r <= 0.001)

        durations = [s.get("duration", 0) or 0 for s in sims]
        avg_time = sum(durations) / len(durations) if durations else 0.0

        terminations: Dict[str, int] = {}
        for s in sims:
            reason = s.get("termination_reason", "unknown")
            terminations[reason] = terminations.get(reason, 0) + 1

        return {
            "total_tasks": total,
            "scored_tasks": scored,
            "mean_reward": mean_reward,
            "full_credit": full_credit,
            "partial": scored - full_credit - zero,
            "zero": zero,
            "avg_duration": avg_time,
            "terminations": terminations,
        }

    def generate_report(self, results: Dict) -> str:
        """Generate a formatted report."""
        lines = [
            "=" * 60,
            "A2A AGENT PAIR - EVALUATION REPORT",
            "=" * 60,
            "",
            f"Tasks run:        {results.get('total_tasks', 0)}",
            f"Mean reward:      {results.get('mean_reward', 0):.3f}   <- score",
            f"Full credit:      {results.get('full_credit', 0)} / {results.get('scored_tasks', 0)}",
            f"Partial credit:   {results.get('partial', 0)}",
            f"Zero reward:      {results.get('zero', 0)}",
            f"Avg duration:     {results.get('avg_duration', 0):.1f}s",
            "",
        ]
        terminations = results.get("terminations", {})
        if terminations:
            lines.append("Termination reasons:")
            for reason, count in sorted(terminations.items(), key=lambda x: -x[1]):
                lines.append(f"   {reason}: {count}")
        if results.get("warning"):
            lines += ["", f"WARNING: {results['warning']}"]
        if results.get("results_dir"):
            lines += ["", f"Results dir: {results['results_dir']}", f"Browse with: uv run tau2 view {results['results_dir']}"]
        lines += ["", "=" * 60]
        return "\n".join(lines)

    def run_full_evaluation(self, split: str = "train", smoke: bool = True) -> bool:
        """Optionally smoke-test, then run the split and report."""
        print("=" * 60)
        print(f"A2A AGENT PAIR - FULL EVALUATION ('{split}' split)")
        print("=" * 60)

        if smoke and not self.run_smoke_test():
            print("\nSmoke test failed, stopping evaluation")
            return False

        results = self.run_eval(split)
        if "error" in results:
            print(f"Evaluation error: {results['error']}")
            return False

        print(self.generate_report(results))

        mean = results.get("mean_reward", 0)
        if mean >= 0.8:
            print("\nEXCELLENT: 0.80+ mean reward")
        elif mean >= 0.6:
            print("\nGOOD: 0.60-0.80 mean reward")
        elif mean >= 0.4:
            print("\nNEEDS IMPROVEMENT: 0.40-0.60 mean reward")
        else:
            print("\nCRITICAL: below 0.40 mean reward")
        return mean >= 0.6


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run A2A agent evaluation via the a2a-hack harness")
    parser.add_argument("--personal-url", default="http://localhost:9001")
    parser.add_argument("--cs-url", default="http://localhost:9002")
    parser.add_argument("--harness-dir", default=str(DEFAULT_HARNESS_DIR))
    parser.add_argument("--tasks", default="train", help="Split (train/test/feedback) or comma-separated task ids")
    parser.add_argument("--output", default=None, help="Results parent dir (default: <harness>/results)")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--no-smoke", action="store_true", help="Skip the pre-run smoke test")

    args = parser.parse_args()

    runner = EvaluationRunner(
        personal_url=args.personal_url,
        cs_url=args.cs_url,
        harness_dir=args.harness_dir,
        output_dir=args.output,
    )

    if args.smoke_only:
        success = runner.run_smoke_test()
    else:
        success = runner.run_full_evaluation(split=args.tasks, smoke=not args.no_smoke)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
