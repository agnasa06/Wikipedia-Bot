import requests
import random
from distance import edit_distance
import queue
import threading
import time

visitedLock = threading.Lock()
totalLock = threading.Lock()

def hit_api(title, params=None, headers=None, method='GET', data=None):
    url = f'https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=links&pllimit=max&format=json'
    try:
        response = None
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers)
        elif method == 'POST':
            response = requests.post(url, params=params, headers=headers, data=data)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            return response.json()  # Assuming the response is in JSON format
        else:
            print(f"API request failed with status code: {response.status_code}")
            print(response.text)  # Print the response content for debugging

    except Exception as e:
        print(f"An error occurred: {e}")

def process_tasks(task_queue, new_queue, depth, thread_number):
    global scanned
    global stop
    pages_done = 0
    while not task_queue.empty() and not stop:
        path, page = task_queue.get()
        pages_done += 1
        if pages_done % 100 == 0:
            print(f"Thread {thread_number} has done {pages_done} pages, there are {task_queue.qsize()} left\n{depth} {path} {page}")
            with totalLock:
                scanned += 20
        data = hit_api(page)
        links = list(data["query"]["pages"].values())[0]
        if "links" not in links:
            continue
        links = links["links"]
        current_visited = set()
        for i in range(len(links)):
            link = links[i]
            if link["title"] in visited:
                continue
            if edit_distance(target, link["title"]) <= 1:
                print(f"Path found!\n{path + [page]} {link['title']}")
                stop = True
            if i != 0 and edit_distance(links[i]["title"], links[i-1]["title"]) <= 2:
                continue
            new_queue.put((path + [page], link["title"]))
            current_visited.add(link["title"])
        with visitedLock:
            visited.update(current_visited)
    with totalLock:
        if pages_done != 0:
            scanned += pages_done % 20
            print(f"Thread {thread_number} has done {pages_done} pages")
    return True

start = "Ruler"
depth = 4
target = "Technoblade"
visited = set()
curr = []
scanned = 0
stop = False
PROCESSES = 200

def main():
    global stop
    current_queue = queue.Queue()
    current_queue.put(([], start))
    try:
        for i in range(depth):
            time_start = time.time()
            scanned_start = scanned
            new_queue = queue.Queue()
            threads = []
            for n in range(PROCESSES):
                p = threading.Thread(target=process_tasks, args=(current_queue, new_queue, i, n))
                threads.append(p)
                p.start()
            for p in threads:
                while p.is_alive():
                    p.join(1)
            print(f"Finished depth {i}")
            print(f"Scanned {scanned - scanned_start} pages in depth")
            print(f"Time taken: {time.time() - time_start}")
            print("-----------------------------------")

            current_queue = new_queue

            if stop:
                break
    except KeyboardInterrupt:
        print("Ctrl-c received! Sending kill to threads...")
        stop = True
        for p in threads:
            while p.is_alive():
                p.join(1)
    print(f"Scanned {scanned} pages in total")

if __name__ == "__main__":
    main()
