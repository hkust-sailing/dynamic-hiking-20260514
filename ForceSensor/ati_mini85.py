import nidaqmx
import numpy as np
from nidaqmx.constants import TerminalConfiguration, AcquisitionType

class ATIMini85:
    def __init__(self, device="Dev1", calibration_file="ForceSensor/config/calibration_matrix.csv"):
        self.device = device
        self.calibration_matrix = np.loadtxt(calibration_file, delimiter=",")
        self.offset = np.zeros(6)  # offset for each channel
        self.task = None
        self.sampling_rate = 1000  # sampling rate (Hz)

    def start(self, sampling_rate=1000):
        """initialize the sensor and start data acquisition"""
        self.sampling_rate = sampling_rate
        self.task = nidaqmx.Task()
        # 6 channels for 6-DOF force sensor
        for i in range(6):
            self.task.ai_channels.add_ai_voltage_chan(
                f"{self.device}/ai{i}",
                terminal_config=TerminalConfiguration.DIFF
            )
        self.task.timing.cfg_samp_clk_timing(
            rate=self.sampling_rate,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=2048  # buffer size
        )
        self.task.start()

    def read_raw_voltages(self, num_samples=10):
        if not self.task:
            raise RuntimeError("Task is not initialized.")
        data = self.task.read(number_of_samples_per_channel=num_samples)
        return np.array(data).T

    def calibrate_zero(self, num_samples=10):
        raw_data = self.read_raw_voltages(num_samples)
        self.offset = np.mean(raw_data, axis=0)

    def get_calibrated_forces(self, num_samples=10):
        raw_data = self.read_raw_voltages(num_samples)
        adjusted_data = raw_data - self.offset
        return np.dot(adjusted_data, self.calibration_matrix.T)

    def stop(self):
        if self.task:
            self.task.stop()
            self.task.close()