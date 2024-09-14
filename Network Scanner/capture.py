import requests
from urllib.parse import urljoin
from mitmproxy import http

# Configure proxies to route traffic through mitmproxy
proxies = {
    "http": "http://localhost:8080",
    "https": "http://localhost:8080",
}

# Define origin and destination URLs
origin_url = "https://a.a23.in/e/aIILGkv8evb"
dest_url = "https://www.a23.com/rummy.html?%24web_only=true&_branch_match_id=1001429025511244630&_branch_referrer=H4sIAAAAAAAAA8soKSkottLXT9RLNDLWy8zTT9VP9PT0cc8us0gtSwIAAXrGFh4AAAA%3D"

# Initialize an empty list to store hops (redirect chain)
hops = []
current_url = origin_url

# Function to capture and log network hops
while True:
    try:
        # Send the request and avoid automatic redirects to capture each hop
        response = requests.get(current_url, proxies=proxies, allow_redirects=False, verify=False)

        if response.is_redirect or response.is_permanent_redirect:
            # Capture the next hop in the redirect chain
            redirect_url = response.headers['Location']
            # Handle relative redirects by resolving to absolute URLs
            redirect_url = urljoin(current_url, redirect_url)
            hops.append((current_url, redirect_url))
            # Update current URL to the redirect URL for the next iteration
            current_url = redirect_url
        else:
            # Final destination reached, log it
            hops.append((current_url, response.url))
            break
    except Exception as e:
        print(f"An error occurred: {e}")
        break

# Display the captured network hops
for i, (src, dst) in enumerate(hops, 1):
    print(f"Hop {i}: {src} -> {dst}")

# Sample mitmproxy script to log request and response data
def request(flow: http.HTTPFlow) -> None:
    print(f"Request URL: {flow.request.url}\n")
    print(f"Request Headers: {flow.request.headers}\n")
    print(f"Request Body: {flow.request.text}\n\n")
#     with open("requests.log", "a") as f:
#         f.write(f"Request URL: {flow.request.url}\n")
#         f.write(f"Request Headers: {flow.request.headers}\n")
#         f.write(f"Request Body: {flow.request.text}\n\n")

def response(flow: http.HTTPFlow) -> None:
    print(f"Response URL: {flow.request.url}\n")
    print(f"Response Headers: {flow.response.headers}\n")
    print(f"Response Body: {flow.response.text}\n\n")
#     with open("responses.log", "a") as f:
#         f.write(f"Response URL: {flow.request.url}\n")
#         f.write(f"Response Headers: {flow.response.headers}\n")
#         f.write(f"Response Body: {flow.response.text}\n\n")

# Run mitmproxy with this script using: `mitmproxy -p 8080 -s capture.py`
