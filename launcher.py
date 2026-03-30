import subprocess
import sys

# Start Streamlit and let it handle browser opening
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
