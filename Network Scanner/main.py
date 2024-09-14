import os
import json
import time
import logging
import requests
from browsermobproxy import Server
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import random
import subprocess
import psutil
from pprint import pprint

# Constants
URL = "https://a.a23.in/e/aIILGkv8evb"
PROXY_PATH = os.getenv('BROWSERMOB_PROXY_PATH', '/home/ankush/Documents/Network_hops/browsermob-proxy-2.1.4/bin/browsermob-proxy')
HAR_FILE = "traffic.har"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_free_port():
    for _ in range(10):  # Try up to 10 times
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', 0))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("Failed to find a free port")


def start_browsermob_proxy():
    try:
        port = find_free_port()
        logging.info(f"Attempting to start BrowserMob Proxy on port {port}.")
        server = Server(PROXY_PATH, options={'port': port})
        server.start()
        logging.info(f"BrowserMob Proxy started on port {port}.")
        time.sleep(1)
        return server, port
    except Exception as e:
        logging.error(f"Failed to start BrowserMob Proxy: {e}")
        raise

def release_port(port):
    """ Forcefully close the port by terminating processes using it. """
    for proc in psutil.process_iter(['pid', 'connections']):
        for conn in proc.info['connections']:
            if conn.laddr.port == port:
                logging.info(f"Terminating process {proc.info['pid']} using port {port}")
                proc.terminate()
                proc.wait()  # Wait for the process to terminate

    # Double-check if port is still in use
    if is_port_in_use(port):
        logging.warning(f"Port {port} is still in use.")
    else:
        logging.info(f"Port {port} successfully released.")

def is_port_in_use(port):
    """ Check if a specific port is in use. """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except OSError:
            return True
        
def stop_browsermob_proxy(server, port):
    try:
        # Check if the server is already None
        if server is not None:
            # Stop the BrowserMob Proxy server
            server.stop()
            logging.info("BrowserMob Proxy stopped.")
        else:
            logging.warning("Server object was None, skipping stop operation.")

        # Ensure the port is closed
        release_port(port)

    except Exception as e:
        logging.error(f"Failed to stop BrowserMob Proxy: {e}")


def capture_traffic(proxy, url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-insecure-localhost')
    options.add_argument(f"--proxy-server={proxy.proxy}")

    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    proxy.new_har("capture", options={
        'captureHeaders': True,
        'captureContent': True,
        'captureBinaryContent': True,
        'trustAllServers': True 
    })

    driver.get(url)

    try:
        # Wait for a specific element or a timeout
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        logging.warning(f"Timed out waiting for page to load: {e}")

    with open(HAR_FILE, "w", encoding="utf-8") as f:
        json.dump(proxy.har, f)
    
    driver.quit()
    logging.info(f"Captured network traffic saved to {HAR_FILE}")

def load_traffic(har_file):
    try:
        with open(har_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
        logging.info("HAR file loaded successfully.")
        return logs['log']['entries']
    except Exception as e:
        logging.error(f"Failed to load HAR file: {e}")
        return []

def measure_response_time(url, headers, proxy):
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers, proxies={'http': proxy, 'https': proxy}, timeout=60)
        end_time = time.time()
        return end_time - start_time, response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None, None
    
def measure_response_time_with_hops(url, headers, proxy):
    session = requests.Session()
    session.max_redirects = 10  # Set maximum redirects (if needed)

    hops = []
    start_time = time.time()
    
    try:
        response = session.get(url, headers=headers, proxies={'http': proxy, 'https': proxy}, timeout=60, allow_redirects=True)
        end_time = time.time()

        # Calculate time for the initial request
        total_time = end_time - start_time
        hop_data = {
            'url': response.url,
            'status_code': response.status_code,
            'response_time': total_time
        }
        hops.append(hop_data)

        # Trace all redirect hops
        for history in response.history:
            hop_data = {
                'url': history.url,
                'status_code': history.status_code,
                'response_time': total_time  # Same for all hops in this case
            }
            hops.append(hop_data)
        
        return hops

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return []


def replay_request(entry, proxy_url):
    url = entry['request']['url']
    headers = {h['name']: h['value'] for h in entry['request']['headers']}
    
    hops = measure_response_time_with_hops(url, headers, proxy_url)
    
    # Check if any valid hops are returned
    if hops:
        for hop in hops:
            logging.info(f"URL: {hop['url']}, Response Time: {hop['response_time']:.2f} seconds, Status Code: {hop['status_code']}")
        return (url, hops[-1]['response_time'])  # Return the last hop's response time
    else:
        logging.warning(f"Failed to measure response time for {url}")
        return (url, None)  # Ensure it returns a tuple even in case of failure


def replay_and_measure(entries, proxy):
    response_times = []
    proxy_url = f"http://{proxy}"

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(replay_request, entry, proxy_url) for entry in entries]
        for future in as_completed(futures):
            result = future.result()
            if result[1] is not None:
                response_times.append(result)
            else:
                logging.warning(f"Failed to measure response time for {result[0]}")
            # Optional: Add random delay to mimic human behavior
            time.sleep(random.uniform(0.1, 0.5))

    logging.info(f"Measured {len(response_times)} valid response times.")
    return response_times

def filter_urls(entries):
    excluded_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.ico', '.svg', '.woff', '.woff2', '.ttf')
    filtered = [entry for entry in entries if not entry['request']['url'].lower().endswith(excluded_extensions)]
    return filtered

def plot_response_times(response_times, limit=20):
    # Filter out None values and sort
    filtered_times = [rt for rt in response_times if rt[1] is not None]
    sorted_times = sorted(filtered_times, key=lambda x: x[1], reverse=True)[:limit]
    
    if not sorted_times:
        logging.warning("No valid response times to plot.")
        return

    urls, times = zip(*sorted_times)
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(urls)), times, color='skyblue')
    plt.xlabel('URL')
    plt.ylabel('Response Time (seconds)')
    plt.title('Top 20 Slowest Response Times')
    plt.xticks(range(len(urls)), [url.split('?')[0] for url in urls], rotation=90)
    plt.tight_layout()
    plt.show()

def get_listening_ports():
    try:
        result = subprocess.check_output(
            "lsof -i -P -n | grep LISTEN | awk '{print $2}' | uniq",
            shell=True
        )
        pids = result.decode().splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching ports: {e}")
        return []
    for pid in pids:
        try:
            print(f"Killing process {pid}")
            subprocess.run(['kill', '-9', pid], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to kill process {pid}: {e}")


def main():
    get_listening_ports()
    
    server, port = start_browsermob_proxy()
    proxy = server.create_proxy()

    # Capture traffic
    capture_traffic(proxy, URL)

    # Load and filter traffic
    entries = load_traffic(HAR_FILE)
    # pprint(entries[0])
    # exit()
    if entries:
        filtered_entries = filter_urls(entries)
        logging.info(f"Total entries: {len(entries)}, Filtered entries: {len(filtered_entries)}")
        response_times = replay_and_measure(filtered_entries, f"localhost:{port}")
        print(response_times)
        plot_response_times(response_times)
    
    stop_browsermob_proxy(server, port)

    get_listening_ports()

if __name__ == "__main__":
    main()
