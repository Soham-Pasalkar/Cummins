import subprocess
import sys
import webbrowser
import time

# Start Streamlit app
process = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait a bit for server to start
time.sleep(3)

# Open browser automatically
webbrowser.open("http://localhost:8501")

# Keep process alive
process.wait()