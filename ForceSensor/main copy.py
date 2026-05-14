import time
import threading
import signal
import csv
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from queue import Queue

from ati_mini85 import ATIMini85
from filters import LowPassFilter
from visualization import ForceVisualizer
from data_writer import DataWriter
import keyboard

# configuration
SAMPLING_RATE = 1000   # sampling rate (Hz)
CUTOFF_FREQ = 10.0     # low-pass filter cutoff frequency (Hz)
SAMPLE_CHUNK = 10      # number of samples to read each time (10 samples = 10ms at 1000Hz)
BUFFER_SIZE = 1000     # data buffer size
USE_FILTER = False     # use filter or not


def data_acquisition(sensor, data_queue, zero_calibration_event):
    """data acquisition thread: read data from sensor and put into queue"""
    try:
        while True:
            forces = sensor.get_calibrated_forces(num_samples=SAMPLE_CHUNK)
            # zero
            if zero_calibration_event.is_set():
                sensor.calibrate_zero()
                print("Zero offset calibrated.")
                zero_calibration_event.clear()
            if not data_queue.full():
                data_queue.put(forces)
            else:
                print("warning: Data queue is full. Data may be lost.")
            time.sleep(0.001) # Small sleep to prevent CPU overload
            
    except KeyboardInterrupt:
        pass

def data_processing(data_queue, filter, data_writer, visualator, recording_event):
    """data processing thread: apply filter to the data"""
    try:
        while True:
            if not data_queue.empty(): 
                forces_batch = data_queue.get()  # get data from queue
                forces_batch = forces_batch.T # [6,1000]
                # 1. filter the forces
                filtered_forces = filter.apply(forces_batch) # [6,1000]
                # TODO: detect force over the safety range
                # 2. extract the latest force data
                lastest_force = filtered_forces[:,-1] # [6, ]
                print(f"Latest force data: {lastest_force}")
                # 3.TODO: apply control algorithm to the data
                # control_signal = controller.update(latest_force, timestamp)
                # visualation
                if visualator is not None:
                    visualator.update_buffers(filtered_forces.T) # update the visualization
                # write data to csv file
                timestamp = time.time()
                data_entry = list(lastest_force)+[timestamp]
                # Only write if recording is enabled:
                if recording_event.is_set():
                    data_writer.enqueue_data(data_entry)

            time.sleep(0.001)
    except KeyboardInterrupt:
        pass

def key_listener(sensor, zero_calibration_event,exit_event, recording_event):
    """keyboard listener thread: listen for key press to trigger zero calibration"""
    try:
        print("Press space to calibrate zero offset.")
        # print("Controls:")
        # print("  Space - Calibrate zero offset")
        # print("  S - Start/Stop recording data")
        # print("  Q - Quit program")
        while not exit_event.is_set():
            key = keyboard.read_key()
            if key == "space":
                zero_calibration_event.set()
            elif key.lower()=='s':
                if recording_event.is_set():
                    recording_event.clear()
                    print("Record data STOPPED!")
                else:
                    recording_event.set()
                    print("Record data STARTED!")
            elif key == "q":
                exit_event.set()
            time.sleep(0.1)
    except KeyboardInterrupt: 
        pass


# 20250314 filter & visualization
"""
if __name__ == "__main__":
    # initialize sensor
    sensor = ATIMini85()
    sensor.start(sampling_rate=SAMPLING_RATE)
    sensor.calibrate_zero()  # calibrate zero offset

    # initialize low-pass filter
    lp_filter = LowPassFilter(CUTOFF_FREQ, SAMPLING_RATE)
    # TODO: initialize controller
    data_queue = Queue(maxsize=2000) # data queue

    # visualization
    visualator = ForceVisualizer(buffer_size=BUFFER_SIZE, update_interval=100)

    # create an event to signal zero calibration
    zero_calibration_event = threading.Event()

    # start data acquisition and processing threads
    producer = threading.Thread(
        target=data_acquisition,
        args=(sensor, data_queue, zero_calibration_event)
    )
    comsuer = threading.Thread(
        target=data_processing,
        args=(data_queue, lp_filter, visualator)
    )

    listener = threading.Thread(
        target=key_listener,
        args=(sensor, zero_calibration_event)
    )

    producer.start()
    comsuer.start()
    listener.start()

    # visualization
    visualator.run() # run the visualization interface

    # clean up
    sensor.stop()
    producer.join()
    comsuer.join()
    listener.join()
    """
# 20250325 read the data, visualization and use keyboard to store to csv file, no filter, !! because of the data speed is 10ms, so keyboard hard to read,change SAMPLE_CHUNK to use keyboard
# if you dont need record flag,just remove the recording_event and related part
if __name__ == "__main__":
    # initialize sensor
    sensor = ATIMini85()
    sensor.start(sampling_rate=SAMPLING_RATE)
    sensor.calibrate_zero()  # calibrate zero offset

    # TODO: initialize controller
    data_queue = Queue(maxsize=2000) # data queue
    # initialize filter
    filter = LowPassFilter(CUTOFF_FREQ, SAMPLING_RATE, num_channels=6, use_filter=USE_FILTER)

    # visualization
    visualator = ForceVisualizer(buffer_size=BUFFER_SIZE, update_interval=100)
    # visualator = None

    # create an event to signal zero calibration and quit the process
    zero_calibration_event = threading.Event()
    exit_event = threading.Event()
    recording_event = threading.Event()

    # write data to csv file
    csv_filename="./forcedata/fa1.csv"
    data_writer = DataWriter(csv_filename)
    data_writer.start()

    # start threads
    threads = [
        threading.Thread(target=data_acquisition, args=(sensor, data_queue, zero_calibration_event)),
        threading.Thread(target=data_processing, args=(data_queue, filter, data_writer, visualator, recording_event)),
        threading.Thread(target=key_listener, args=(zero_calibration_event, exit_event,recording_event))
    ]
    for t in threads:
        t.start()

    # Run visualization if enabled
    if visualator is not None:
        visualator.run()
    
    # Wait for exit signal
    while not exit_event.is_set():
        time.sleep(0.1)
        
    # Clean up
    print("Shutting down...")
    recording_event.clear() # ensure recording is stopped
    data_writer.stop()
    sensor.stop()
    
    for t in threads:
        t.join()
    # start data acquisition and processing threads
    """
    producer = threading.Thread(
        target=data_acquisition,
        args=(sensor, data_queue, zero_calibration_event)
    )
    comsuer = threading.Thread(
        target=data_processing,
        args=(data_queue, filter, data_writer)
    )

    listener = threading.Thread(
        target=key_listener,
        args=(sensor, zero_calibration_event,exit_event)
    )

    producer.start()
    comsuer.start()
    listener.start()

    # visualization
    # visualator.run() # run the visualization interface

    # listen the keyboard
    listener.join()

    # stop data record and process thread
    # data_queue.put(None)
    producer.join()
    comsuer.join()
 
    # stop record the data
    data_writer.stop()
    # clean up
    sensor.stop()"""

    print("data recorded and saved as:",csv_filename)

    
    

"""
if __name__ == "__main__":
    # initialize sensor
    sensor = ATIMini85()
    sensor.start(sampling_rate=SAMPLING_RATE)
    sensor.calibrate_zero()  # calibrate zero offset

    # initialize low-pass filter
    lp_filter = LowPassFilter(CUTOFF_FREQ, SAMPLING_RATE)

    # initialize data queue
    data_queue = Queue(maxsize=1000)

    # start data acquisition and processing threads
    producer = threading.Thread(
        target=data_acquisition,
        args=(sensor, data_queue)
    )
    consumer = threading.Thread(
        target=data_processing,
        args=(data_queue, lp_filter)
    )

    producer.start()
    consumer.start()

    try:
        while True:
            time.sleep(1)  # main thread sleeps for 1 second
    except KeyboardInterrupt:
        print("\nStopping acquisition...")
        sensor.stop()
        producer.join()
        consumer.join()

    app = pg.mkQApp()
    win = pg.GraphicsLayoutWidget(title="ATI mini85 6-axis force real-time monitor")
    win.resize(1200, 800)

    # Create 6 subplots.
    plots = [win.addPlot(row=i, col=0, title=name) for i, name in enumerate(['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz'])]
    curves = [p.plot(pen=pg.intColor(i)) for i, p in enumerate(plots)]

    # Initialize data buffers.
    buffer_size = 200
    data_buffers = [np.zeros(buffer_size) for _ in range(6)]

    def update():
        # Read data from DAQ (assumed integrated as global variables).
        global voltages, processed_forces
        if voltages is not None:
            # Update buffers.
            for i in range(6):
                data_buffers[i] = np.roll(data_buffers[i], -len(voltages))
                data_buffers[i][-len(voltages):] = processed_forces[:, i]
                curves[i].setData(data_buffers[i])

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(30)  # Refresh rate approx. 33 Hz.

    win.show()
    app.exec_()"
    """