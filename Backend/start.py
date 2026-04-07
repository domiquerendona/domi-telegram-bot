import os
import subprocess

run_api = os.environ.get("RUN_API", "NOT_SET")
port = os.environ.get("PORT", "8000")
print(f"[start.py] RUN_API={run_api!r}  PORT={port!r}", flush=True)

if run_api == "1":
    print("[start.py] Iniciando uvicorn (API)", flush=True)
    subprocess.run(["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", port])
else:
    print("[start.py] Iniciando bot (main.py)", flush=True)
    subprocess.run(["python", "main.py"])
