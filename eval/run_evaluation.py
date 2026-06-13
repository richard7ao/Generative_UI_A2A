"""Evaluation runner for A2A Customer Service Agent.

Runs evaluation against the A2A harness and generates detailed reports.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class EvalResult:
    """Result of a single evaluation."""
    task_id: str
    passed: bool
    score: float
    response_time: float
    errors: List[str]
    tools_used: List[str]
    research_called: bool


class EvaluationRunner:
    """Runs evaluation and generates reports."""
    
    def __init__(
        self,
        personal_url: str = "http://localhost:9001",
        cs_url: str = "http://localhost:9002",
        output_dir: str = "results"
    ):
        self.personal_url = personal_url
        self.cs_url = cs_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.results: List[EvalResult] = []
    
    def run_smoke_test(self) -> bool:
        """Run basic smoke test."""
        print("🔄 Running smoke test...")
        
        try:
            # Import harness module if available
            result = subprocess.run(
                [
                    "python3", "-m", "a2a_hack",
                    "smoke",
                    "--personal-url", self.personal_url,
                    "--cs-url", self.cs_url
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            passed = result.returncode == 0
            
            if passed:
                print("✅ Smoke test PASSED")
            else:
                print("❌ Smoke test FAILED")
                print(result.stderr)
            
            return passed
            
        except Exception as e:
            print(f"❌ Smoke test error: {e}")
            return False
    
    def run_train_eval(self, max_tasks: int = None) -> Dict:
        """Run evaluation on train split."""
        print("🔄 Running train split evaluation...")
        
        results_path = self.output_dir / f"train_{int(time.time())}.json"
        
        try:
            cmd = [
                "python3", "-m", "a2a_hack",
                "run",
                "--personal-url", self.personal_url,
                "--cs-url", self.cs_url,
                "--tasks", "train",
                "--save-to", str(results_path),
                "--auto-resume"
            ]
            
            if max_tasks:
                cmd.extend(["--max-tasks", str(max_tasks)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )
            
            # Parse results
            if results_path.exists():
                with open(results_path) as f:
                    data = json.load(f)
                return self._analyze_results(data)
            else:
                return {"error": "No results file generated"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_results(self, data: Dict) -> Dict:
        """Analyze evaluation results."""
        total = len(data.get("tasks", []))
        passed = sum(1 for t in data["tasks"] if t.get("passed", False))
        failed = total - passed
        
        # Calculate metrics
        success_rate = passed / total if total > 0 else 0
        
        # Response times
        times = [t.get("duration", 0) for t in data["tasks"]]
        avg_time = sum(times) / len(times) if times else 0
        
        # Error analysis
        errors = {}
        for task in data["tasks"]:
            if not task.get("passed", False):
                error_type = task.get("error_type", "unknown")
                errors[error_type] = errors.get(error_type, 0) + 1
        
        return {
            "total_tasks": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "avg_response_time": avg_time,
            "errors_by_type": errors
        }
    
    def generate_report(self, results: Dict) -> str:
        """Generate formatted report."""
        lines = [
            "=" * 60,
            "A2A CUSTOMER SERVICE AGENT - EVALUATION REPORT",
            "=" * 60,
            "",
            f"📊 Total Tasks: {results.get('total_tasks', 0)}",
            f"✅ Passed: {results.get('passed', 0)}",
            f"❌ Failed: {results.get('failed', 0)}",
            f"📈 Success Rate: {results.get('success_rate', 0):.1%}",
            "",
            f"⏱️  Average Response Time: {results.get('avg_response_time', 0):.2f}s",
            "",
        ]
        
        # Error breakdown
        errors = results.get('errors_by_type', {})
        if errors:
            lines.append("⚠️  Errors by Type:")
            for error_type, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"   {error_type}: {count}")
        else:
            lines.append("✅ No errors detected!")
        
        lines.extend([
            "",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def save_report(self, report: str, filename: str = "eval_report.txt"):
        """Save report to file."""
        report_path = self.output_dir / filename
        with open(report_path, "w") as f:
            f.write(report)
        print(f"📄 Report saved to: {report_path}")
    
    def run_full_evaluation(self):
        """Run complete evaluation suite."""
        print("=" * 60)
        print("A2A CUSTOMER SERVICE AGENT - FULL EVALUATION")
        print("=" * 60)
        print()
        
        # Step 1: Smoke test
        if not self.run_smoke_test():
            print("\n❌ Smoke test failed, stopping evaluation")
            return False
        
        print()
        
        # Step 2: Train split evaluation
        print("🔄 Starting train split evaluation...")
        print("   (This may take several minutes)")
        print()
        
        results = self.run_train_eval(max_tasks=10)  # Start with 10 tasks
        
        if "error" in results:
            print(f"❌ Evaluation error: {results['error']}")
            return False
        
        # Generate and display report
        report = self.generate_report(results)
        print(report)
        
        # Save report
        self.save_report(report)
        
        # Summary
        success_rate = results.get('success_rate', 0)
        if success_rate >= 0.8:
            print("\n🎉 EXCELLENT: 80%+ success rate!")
        elif success_rate >= 0.6:
            print("\n✅ GOOD: 60-80% success rate")
        elif success_rate >= 0.4:
            print("\n⚠️  NEEDS IMPROVEMENT: 40-60% success rate")
        else:
            print("\n❌ CRITICAL: Below 40% success rate")
        
        return success_rate >= 0.6  # Consider 60%+ as passing


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run A2A Agent Evaluation")
    parser.add_argument("--personal-url", default="http://localhost:9001")
    parser.add_argument("--cs-url", default="http://localhost:9002")
    parser.add_argument("--output", default="results")
    parser.add_argument("--smoke-only", action="store_true")
    
    args = parser.parse_args()
    
    runner = EvaluationRunner(
        personal_url=args.personal_url,
        cs_url=args.cs_url,
        output_dir=args.output
    )
    
    if args.smoke_only:
        success = runner.run_smoke_test()
    else:
        success = runner.run_full_evaluation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
