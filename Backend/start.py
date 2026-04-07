import os
import subprocess

if os.environ.get("RUN_API") == "1":
    port = os.environ.get("PORT", "8000")
    subprocess.run(["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", port])
else:
    subprocess.run(["python", "main.py"])
