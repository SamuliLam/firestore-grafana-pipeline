import requests
import time
import subprocess
import json

# Start ngrok
subprocess.Popen(['ngrok', 'http', '8000'])
time.sleep(2)  # Wait for ngrok to start

# Get the ngrok URL from ngrok's local API
response = requests.get('http://127.0.0.1:4040/api/tunnels')
tunnels = response.json()['tunnels']
public_url = tunnels[0]['public_url']

print(f"Your webhook URL is: {public_url}/webhook")

# Log the url
with open("ngrok_url.txt", "w") as f:
    f.write(public_url)
