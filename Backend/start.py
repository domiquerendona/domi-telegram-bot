import os
import subprocess

port = os.environ.get("PORT", "8000")
has_token = bool(os.environ.get("BOT_TOKEN"))
print(f"[start.py] BOT_TOKEN={'SET' if has_token else 'NOT_SET'}  PORT={port!r}", flush=True)

if has_token:
    print("[start.py] Iniciando bot (main.py)", flush=True)
    subprocess.run(["python", "main.py"])
else:
    print("[start.py] Iniciando API (uvicorn)", flush=True)
    subprocess.run(["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", port])
