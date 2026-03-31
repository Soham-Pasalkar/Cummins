import subprocess
import sys
import os
import webbrowser
import time

# Get correct path inside EXE or dev mode
base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
app_path = os.path.join(base_path, "app.py")

print("Running from:", base_path)
print("App path:", app_path)

# Start Streamlit server
proc = subprocess.Popen([
    sys.executable,
    "-m", "streamlit",
    "run", app_path,
    "--server.headless=true",        # run in background, no prompt
])

# Wait a bit to let the server start
time.sleep(2)

# Open browser automatically
webbrowser.open("http://localhost:8501")

# Optional: keep the launcher alive until Streamlit exits
# (user can close the browser + task manager kill if needed)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
