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
PROXY_PATH = os.getenv('BROWSERMOB_PROXY_PATH', 'D:/Python_Projects/Network Scanner/browsermob-proxy/browsermob-proxy-2.1.4/bin/browsermob-proxy')
HAR_FILE = "traffic.har"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_free_port():
    for _ in range(10):
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
        logging.info("Server initialized, starting...")
        server.start()
        logging.info(f"BrowserMob Proxy started on port {port}.")
        time.sleep(1)
        return server, port
    except Exception as e:
        logging.error(f"Failed to start BrowserMob Proxy: {e}")
        raise


def release_port(port):
    for proc in psutil.process_iter(['pid', 'connections']):
        for conn in proc.info['connections']:
            if conn.laddr.port == port:
                logging.info(f"Terminating process {proc.info['pid']} using port {port}")
                proc.terminate()
                proc.wait()

def stop_browsermob_proxy(server, port):
    try:
        if server is not None:
            server.stop()
            logging.info("BrowserMob Proxy stopped.")
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
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

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

def measure_response_time_with_hops(url, headers, proxy):
    session = requests.Session()
    session.max_redirects = 10 
    hops = []
    
    start_time = time.time()
    
    try:
        response = session.get(url, headers=headers, proxies={'http': proxy, 'https': proxy}, timeout=60, allow_redirects=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        hop_data = {
            'url': response.url,
            'status_code': response.status_code,
            'response_time': total_time 
        }
        
        hops.append(hop_data)
        
        for history in response.history:
            hop_data = {
                'url': history.url,
                'status_code': history.status_code,
                'response_time': total_time 
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
    
    if hops:
        for hop in hops:
            logging.info(f"URL: {hop['url']}, Response Time: {hop['response_time']:.2f} seconds, Status Code: {hop['status_code']}")
        
        return (url, hops[-1]['response_time'])
    
    else:
        logging.warning(f"Failed to measure response time for {url}")
        return (url, None)

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
                
            time.sleep(random.uniform(0.1, 0.5))
            
    logging.info(f"Measured {len(response_times)} valid response times.")
    
    return response_times

def filter_urls(entries):
    excluded_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.ico', '.svg', '.woff', '.woff2', '.ttf')
    
    filtered = [entry for entry in entries if not entry['request']['url'].lower().endswith(excluded_extensions)]
    
    return filtered

def plot_response_times(response_times):
    filtered_times = [rt for rt in response_times if rt[1] is not None]
    
    sorted_times = sorted(filtered_times, key=lambda x: x[1], reverse=True)[:20]
    
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

import psutil

def get_listening_ports():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Iterate over the connections of the process
            for conn in proc.connections(kind='inet'):
                # Check if the connection is in the 'LISTEN' state and match the port you want to check
                if conn.status == 'LISTEN' and conn.laddr.port == 59259:  # Change to the desired port
                    print(f"Killing process {proc.info['pid']} ({proc.info['name']}) using port {conn.laddr.port}")
                    proc.terminate()
                    proc.wait()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # Handle any errors related to access or process termination



def main(url):
    get_listening_ports()
    
    server, port = start_browsermob_proxy()
    
    proxy = server.create_proxy()
    
    capture_traffic(proxy, url)

    entries = load_traffic(HAR_FILE)

    if entries:
        filtered_entries = filter_urls(entries)
        
        logging.info(f"Total entries: {len(entries)}, Filtered entries: {len(filtered_entries)}")
        
        response_times = replay_and_measure(filtered_entries, f"localhost:{port}")
        
        logging.info(response_times)
        
        plot_response_times(response_times)

    stop_browsermob_proxy(server, port)

if __name__ == "__main__":
    main(URL)  # Directly call the main function with the URL parameter
