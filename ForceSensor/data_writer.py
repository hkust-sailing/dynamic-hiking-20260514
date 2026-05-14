import csv
from queue import Queue
import threading
import time

class DataWriter:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.queue = Queue(maxsize=5000)
        self.thread = None
        self.running = False
        self.write_count = 0
        self.last_write_time = time.time()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._write_loop, daemon=True)
        self.thread.start()
        print(f"Data writer started, saving to {self.csv_file}")

    def _write_loop(self):
        with open(self.csv_file, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # csv_writer.writerow(['Timestamp', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz'])
            while self.running or not self.queue.empty():
                try:
                    data_entry = self.queue.get(timeout=0.1)
                    if data_entry is not None:
                        csv_writer.writerow(data_entry)
                        self.write_count+=1
                        if self.write_count % 100 ==0:
                            csv_file.flush()
                    self.queue.task_done()
                except:
                    continue
    
    def enqueue_data(self, data_entry):
        if not self.queue.full():
            self.queue.put(data_entry)
        else:
            print("Warning: DataWriter queue full - data dropped")

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        print(f"Data writer stopped. Total records written: {self.write_count}")