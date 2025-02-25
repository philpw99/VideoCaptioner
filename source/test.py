import subprocess

try:
    process = subprocess.run( ["ffmpegg", "-version"], capture_output=True, text=True)
    code = process.returncode
    print(f"return: {code}")
except FileNotFoundError:
    print("Not found")
    
