import subprocess
import sys

subprocess.run([
    sys.executable,
    "-m", "streamlit",
    "run", "app.py",
    "--server.headless=false"
])