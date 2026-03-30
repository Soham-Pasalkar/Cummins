import subprocess
import sys
import os

# Get correct path inside EXE
base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
app_path = os.path.join(base_path, "app.py")

print("Running from:", base_path)
print("App path:", app_path)

subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])