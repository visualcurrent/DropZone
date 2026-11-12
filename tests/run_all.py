"""Run every DropZone test in sequence; exit non-zero if any fails."""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = ["test_upload_memory.py", "test_queue_feedback.py", "test_zip_streaming.py", "test_download_range.py",
         "test_download_filename.py", "test_thumb.py"]
fails = []
for t in TESTS:
    print(f"\n===== {t} =====")
    if subprocess.run([sys.executable, os.path.join(HERE, t)]).returncode != 0:
        fails.append(t)
print("\n==================================")
print("ALL TESTS PASSED" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
