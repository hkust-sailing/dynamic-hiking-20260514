import numpy as np
from scipy.signal import butter, lfilter, lfilter_zi


def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs 
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low')
    return b, a
"""
class LowPassFilter:
    def __init__(self, cutoff, fs, num_channels=6):
        self.b, self.a = butter_lowpass(cutoff, fs)
        self.num_channels = num_channels
        self.zi = lfilter_zi(self.b, self.a).reshape(1, -1).repeat(num_channels, axis=0)
        

    def apply(self, data):
        '''Apply low-pass filter to the data'''
        if data.shape[0] != self.num_channels:
            raise ValueError(f"Expected data with {self.num_channels} channels, but got {data.shape[0]} channels.")
        filtered, self.zi = lfilter(self.b, self.a, data, axis=1, zi=self.zi)
        return filtered
    """
class BaseFliter:
    def apply(self, data):
        raise NotImplementedError("Subclasses must implement apply method")
    
class NoOpFilter(BaseFliter):
    def apply(self, data):
        return data
    
class LowPassFilter(BaseFliter):
    def __init__(self, cutoff, fs, num_channels=6, use_filter=True):
        self.use_filter = use_filter
        self.num_channels = num_channels
        if self.use_filter:
            self.b, self.a = butter_lowpass(cutoff, fs)            
            self.zi = lfilter_zi(self.b, self.a).reshape(1, -1).repeat(num_channels, axis=0)
        else:
            self.b = None
            self.a = None
            self.zi = None

    def apply(self, data):
        '''Apply low-pass filter to the data'''
        if not self.use_filter:
            return data
        if data.shape[0] != self.num_channels:
            raise ValueError(f"Expected data with {self.num_channels} channels, but got {data.shape[0]} channels.")
        filtered, self.zi = lfilter(self.b, self.a, data, axis=1, zi=self.zi)
        return filtered
