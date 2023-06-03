import os
import socks
import socket
import requests
import logging
from threading import Thread
from queue import Queue
import configparser

config = configparser.ConfigParser()
config.read('data/config.ini')
proxy_path = config['DEFAULT']['proxy_path']
test_proxy = config['DEFAULT']['test_proxy_path']
max_threads = int(config['DEFAULT']['max_threads'])

def check_proxy(proxy):
    try:
        socks.set_default_proxy(socks.SOCKS4, proxy.split(':')[0], int(proxy.split(':')[1]))
        socket.socket = socks.socksocket
        response = requests.get('https://nyaa.si', timeout=5)
        if response.status_code == 200:
            print(f"Proxy {proxy} is working")
            return True
    except:
        return False

def worker(queue):
    while not queue.empty():
        proxy = queue.get()
        if check_proxy(proxy):
            with open(proxy_path, 'a') as f:
                f.write(proxy + '\n')
        queue.task_done()

def check_proxies():
    if not os.path.exists(test_proxy):
        logging.error("Test proxy file not found")

    with open(proxy_path, 'w') as f:
        pass

    queue = Queue()
    with open(test_proxy, 'r') as f:
        for line in f:
            proxy = line.strip()
            queue.put(proxy)

    threads = []
    for _ in range(max_threads*100):
        t = Thread(target=worker, args=(queue,))
        t.start()
        threads.append(t)

    queue.join()
    for t in threads:
        t.join()

    logging.info("Proxy check complete")

if __name__ == '__main__':
    check_proxies()
