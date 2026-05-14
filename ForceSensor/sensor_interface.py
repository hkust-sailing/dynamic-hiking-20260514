import threading
import numpy as np
import nidaqmx
from queue import Queue
from nidaqmx.constants import TerminalConfiguration, AcquisitionType

class ATISensor:
    def __init__(self, calibration_file="config/sensor_calibration.csv"):
        self.device = "Dev1"
        self.calibration_matrix = np.loadtxt(calibration_file, delimiter=",")
        self.offset = np.zeros(6)
        self.task = None
        self.sampling_rate = 1000 # Hz
        self.data_queue = Queue(maxsize=1000)  # store 1000 data points for output
        self._running = False # flag for thread running

    def start(self, sampling_rate=1000): # sampling rate 1000 Hz, 1ms
        '''initialize the sensor and start the acquisition thread'''
        self.sampling_rate = sampling_rate
        self._running = True
        self._init_daq_task()
        self.thread = threading.Thread(target=self._acquisition_loop)
        self.thread.start()

    def _init_daq_task(self):
        '''initialize the DAQ task'''
        self.task = nidaqmx.Task()
        for i in range(6):
            self.task.ai_channels.add_ai_voltage_chan(
                physical_channel=f"{self.device}/ai{i}",
                terminal_config=TerminalConfiguration.DIFF
            )
        self.task.timing.cfg_samp_clk_timing(
            rate=self.sampling_rate,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=1024
        )
        self.task.start()
    
    

    def _acquisition_loop(self, number_of_samples_per_channel=10):
        '''acquisition loop for the sensor'''
        try:
            while self._running:
                raw_voltage = self.task.read(number_of_samples_per_channel) # [6,10], 10ms, then can change the number.
                adjusted_voltage =  np.array(raw_voltage).T - self.offset # [10,6] 
                force = np.dot(adjusted_voltage, self.calibration_matrix.T) # [10,6]
                self.data_queue.put(force) # put the force data into the queue
        except Exception as e:
            print(f'Sensor error in acquisition loop: {e}')
        finally:
            self.task.stop()
            self.task.close()

    def stop(self):
        '''stop the sensor acquisition thread'''
        self._running = False
        self.thread.join()





