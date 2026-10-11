"""Demo: record sample failures, then check a new task for warnings.

Run:  python demo.py
Needs GROQ_API_KEY in .env (see .env.example).
"""
import os

from fpm.engine import FailurePatternMemory

DB_PATH = "demo.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)  # start fresh each run

fpm = FailurePatternMemory(db_path=DB_PATH)

print("=== Recording failures ===\n")

failures = [
    ("ModuleNotFoundError: No module named 'requests'", "script_run"),
    ("Agent B received hallucinated output from Agent A and propagated it", "multi_agent"),
    ("pytest failed: assertion error in test_user_auth due to stale mock", "testing"),
    ("OpenAI API returned 429 rate limit during batch processing", "api_call"),
]

for log, task in failures:
    fid = fpm.record_failure(log, task_type=task, agent_id="demo")
    print(f"  Recorded: {fid}")

print("\n=== Checking for warnings ===\n")

warnings = fpm.check_before_task("run python script that imports requests library")

if not warnings:
    print("  No warnings found.")
for w in warnings:
    print(f"  [{w.similarity:.2f}] {w.context_pattern}")
    print(f"      Prevention: {w.prevention}")
    print(f"      Severity: {w.severity}\n")

print(f"Done. Build the dashboard with: python dashboard.py {DB_PATH}")
