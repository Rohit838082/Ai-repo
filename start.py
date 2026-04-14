import os
import subprocess
import time
import urllib.request
import threading

def start_backend():
    print("Starting FastAPI Backend...")
    # Using python -m uvicorn instead of directly uvicorn to ensure it runs from current python environment
    subprocess.Popen(["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"])

def setup_tunnel():
    print("Setting up Cloudflare Tunnel...")
    # Download cloudflared if not exists
    if not os.path.exists("cloudflared-linux-amd64"):
        urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", "cloudflared-linux-amd64")
        os.chmod("cloudflared-linux-amd64", 0o777)
    
    # Run cloudflared
    tunnel = subprocess.Popen(["./cloudflared-linux-amd64", "tunnel", "--url", "http://127.0.0.0:8000"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for line in iter(tunnel.stdout.readline, ''):
        if "trycloudflare.com" in line:
            url = [word for word in line.split() if "trycloudflare.com" in word]
            if url:
                print("\n" + "="*60)
                print(f"🚀 UI is available at: {url[0]}")
                print("="*60 + "\n")
                break

if __name__ == "__main__":
    t1 = threading.Thread(target=start_backend)
    t1.start()
    time.sleep(2) # Give FastAPI time to start
    setup_tunnel()
    t1.join()
