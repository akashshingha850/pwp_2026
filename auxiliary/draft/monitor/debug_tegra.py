import subprocess
import time
import re

def test_tegrastats():
    try:
        print("Starting tegrastats...")
        # Use --interval 1000 to force output every second
        proc = subprocess.Popen(['tegrastats', '--interval', '1000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("Waiting for output...")
        
        # Read one line
        line = proc.stdout.readline()
        print(f"Read line: {line!r}")
        
        if not line:
             # Try stderr
             err = proc.stderr.read()
             print(f"Stderr: {err}")
        
        proc.terminate()
        
        if line:
            # Test regex
            gpu_match = re.search(r'GR3D_FREQ (\d+)%', line)
            if gpu_match:
                print(f"GPU Match: {gpu_match.group(1)}")
            else:
                print("GPU Regex No Match")
                
            temp_match = re.search(r'cpu@([\d.]+)C', line)
            if temp_match:
                print(f"Temp Match: {temp_match.group(1)}")
            else:
                print("Temp Regex No Match")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_tegrastats()