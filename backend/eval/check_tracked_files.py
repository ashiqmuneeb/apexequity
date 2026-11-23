import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def check_tracked():
    print("==================================================================")
    print("TASK 9: TRACKED FILES AND DEPENDENCY CHECK (READ-ONLY)")
    print("==================================================================")

    # 1. Check status of directories
    dirs_to_check = ["backend/app", "backend/eval", "backend/tests", "frontend/src"]
    for d in dirs_to_check:
        print(f"\n--- Git status for {d} ---")
        res = subprocess.run(["git", "status", "--short", d], cwd=str(ROOT_DIR), capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()
        if not lines:
            print("  Clean (no untracked or modified files)")
        else:
            for l in lines:
                print(f"  {l}")

    # 2. Check key runtime files
    runtime_files = [
        "backend/app/main.py",
        "backend/app/core/config.py",
        "backend/app/services/retrieval_service.py",
        "backend/app/services/deterministic_lookup.py",
        "backend/app/services/number_validator.py",
        "backend/app/services/analysis_service.py",
        "backend/app/services/rag_engine.py",
        "backend/eval/golden.jsonl",
        "backend/eval/golden_v2_heldout.jsonl",
        "backend/eval/run.py",
        "backend/eval/metrics.py",
        "backend/eval/cache.py",
        "frontend/src/App.tsx",
        "frontend/package.json",
    ]

    print("\n--- Runtime Files Tracking & Ignore Verification ---")
    for f in runtime_files:
        ls_res = subprocess.run(["git", "ls-files", f], cwd=str(ROOT_DIR), capture_output=True, text=True)
        is_tracked = bool(ls_res.stdout.strip())
        ig_res = subprocess.run(["git", "check-ignore", f], cwd=str(ROOT_DIR), capture_output=True, text=True)
        is_ignored = bool(ig_res.stdout.strip())

        status_str = "TRACKED & NOT IGNORED" if (is_tracked and not is_ignored) else f"WARNING: tracked={is_tracked}, ignored={is_ignored}"
        print(f"  {f:<45}: {status_str}")

if __name__ == "__main__":
    check_tracked()

