import requests
import random
import sys
from distance import edit_distance
import queue
import threading
import time
import heapq

from sematch.semantic.similarity import WordNetSimilarity
wns = WordNetSimilarity()

import warnings
warnings.filterwarnings("ignore")

visitedLock = threading.Lock()
totalLock = threading.Lock()

def hit_api(title, params=None, headers=None, data=None):
    url = f'https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=links&pllimit=max&format=json'
    try:
        response = requests.get(url, params=params, headers=headers)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            return response.json()  # Assuming the response is in JSON format
        else:
            print(f"API request failed with status code: {response.status_code}")
            #print(response.text)  # Print the response content for debugging

    except Exception as e:
        print(f"An error occurred: {e}")

def process_tasks(task_queue, new_queue, depth, thread_number):
    global scanned
    global stop
    pages_done = 0
    while not task_queue.empty() and not stop:
        path, page = task_queue.get()
        pages_done += 1
        print(depth, path, page, wns.word_similarity(page, target, 'lin'), target)
        if pages_done % 100 == 0:
            print(f"Thread {thread_number} has done {pages_done} pages, there are {task_queue.qsize()} left\n{depth} {path} {page}")
       # print(depth, path, page)
        data = hit_api(page)
        links = list(data["query"]["pages"].values())[0]["links"]
        current_visited = set()
        links = [link["title"] for link in links if link["title"] not in visited]
        #print([(link, wns.word_similarity(link, target, 'li')) for link in links])
        #print(sorted(links, key=lambda x: wns.word_similarity(x, target, 'li')))
        scores = []
        for link in links:
            if edit_distance(target, link) <= 1 and wns.word_similarity(link, target, 'lin') > 0.8:
                stop = True
                paths.append((path + [page], link))
            try:
                score = wns.word_similarity(link, target, 'lin')
                # if depth >= 6:
                #     print(link, score)
                if depth <= 2 or score > 0.1 + 0.04 * depth:
                    scores.append((link, score))
            except:
                pass
        to_visit = heapq.nlargest(10, scores, key=lambda x: x[1])
        if depth >= 6:
            print(to_visit)
            print(scores)
        #print(to_visit)
        for link, score in to_visit:
            if link not in visited:
                new_queue.put((path + [page], link))
                current_visited.add(link)
        with visitedLock:
            visited.update(current_visited)
    if pages_done != 0:
        with totalLock:
            scanned += pages_done
            # print(f"Thread {thread_number} has done {pages_done} pages")
    return True


if len(sys.argv) < 3:
    print("Usage: python3 wikipedia-heuristic.py <start> <target>")
    exit(1)
start = sys.argv[1]
target = sys.argv[2]
depth = 10
visited = set()
curr = []
paths = []
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
            for n in range(min(current_queue.qsize(), PROCESSES)):
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
                print(f"Paths found!")
                for path in paths:
                    print(path[0], path[1])
                break
    except KeyboardInterrupt:
        print("Ctrl-c received! Sending kill to threads...")
        stop = True
        for p in threads:
            while p.is_alive():
                #print(p)
                p.join(1)
    print(f"Scanned {scanned} pages in total")

if __name__ == "__main__":
    main()
