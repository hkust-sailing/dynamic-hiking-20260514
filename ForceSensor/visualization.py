import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

import sys
import os
import csv

class ForceVisualizer:
    def __init__(self, buffer_size=200, update_interval=30):
        """
        init the real-time force visualizer
        :param buffer_size: data buffer size (default to keep 200 historical points)
        :param update_interval: interface refresh interval (milliseconds)
        """
        self.app = pg.mkQApp()
        self.win = pg.GraphicsLayoutWidget(title="ATI mini85 6-axis force real-time monitor")
        self.win.resize(1200, 800)
        
        # 6 subplots
        self.plots = [self.win.addPlot(row=i, col=0, title=name) 
                     for i, name in enumerate(['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz'])]
        self.curves = [p.plot(pen=pg.intColor(i)) for i, p in enumerate(self.plots)]
        
        # Create a single plot for all channels
        # self.plot = self.win.addPlot(title="6D Force Data")
        # # # self.curves = [self.plot.plot(pen=pg.intColor(i)) for i in range(6)]  # Create one curve for each channel
        
        # self.plot.addLegend() # legend
        # channel_names = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']
        # self.curves = []
        # for i in range(6):
        #     curve = self.plot.plot(pen=pg.intColor(i), name = channel_names[i])
        #     self.curves.append(curve)

        # initialize data buffer
        self.buffer_size = buffer_size
        self.data_buffers = [np.zeros(buffer_size) for _ in range(6)]
        
        # setup a timer for interface update
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(update_interval)
    
    def update_buffers(self, new_forces):
        """
        Update the data buffer with new forces
        :param new_forces: new 6D force data (shape [N,6])
        """
        for i in range(6):
            # Update the data buffer
            self.data_buffers[i] = np.roll(self.data_buffers[i], -len(new_forces))
            self.data_buffers[i][-len(new_forces):] = new_forces[:, i]
    
    def update(self):
        """Update the interface with new data"""
        try:
            for i in range(6):
                self.curves[i].setData(self.data_buffers[i])
        except KeyboardInterrupt:
            pass
    
    def run(self):
        """Run the visualization interface"""
        self.win.show()
        try:
            self.app.exec()
        except KeyboardInterrupt:
            self.timer.stop()
            self.win.close()
            self.app.quit()

# 6-axis real-time plot
class RealTimePlot:
    def __init__(self):
        # self.app = pg.mkQApp()
        self.app = QtWidgets.QApplication(sys.argv)
        self.win = pg.GraphicsLayoutWidget(title="Real-time Monitoring")
        # data 
        self.buffer_size = 200
        self.cycle = 0.01
        self.time = np.linspace(-self.buffer_size*self.cycle, 0, self.buffer_size) # time cycle 10ms
        
        self.plots = [self.win.addPlot(row=i, col=0) for i in range(6)] # 6 subplots for 6 axis
        self.win.nextRow()
        self.pos_plot = self.win.addPlot(title="Position Tracking")
        self.pos_curve = self.pos_plot.plot(pen='y')
        self.pos_data = np.zeros((6, 200))

        # Position Monitor
        self.target_pos_data = np.zeros((6, self.buffer_size)) # x: give robot, not x_d!!!
        self.actual_pos_data = np.zeros((6, self.buffer_size)) # real_x: feedback from robot
        self.target_pos_curves = []
        self.actual_pos_curves = []
        pos_unit = ['mm', 'mm', 'mm', 'deg', 'deg', 'deg']
        for i, plot in enumerate(self.plots):
            plot.setLabel('left', f'Axis {i+1}', pos_unit[i])
            plot.setLabel('bottom', 'Time', 's')
            plot.addLegend()
            target = plot.plot(pen=pg.mkPen('r', width=2), name='Target')
            actual = plot.plot(pen=pg.mkPen('b', width=1.5), name='Actual')
            self.target_pos_curves.append(target)
            self.actual_pos_curves.append(actual)

        # Force Monitor
        self.force_plot = self.win.addPlot(title="Force Feedback")
        self.force_plot.setLabel('left', 'Force', 'N/Nm')
        self.force_plot.setLabel('bottom', 'Time', 's')
        self.force_curve = self.force_plot.plot(pen='r')
        self.force_data = np.zeros((6, self.buffer_size))

        self.win.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        # self.timer.timeout.connect(self.update_data)
        self.timer.start(100)
        
    def update(self, target_pos, actual_pos, force):
        self.target_pos_data = np.roll(self.target_pos_data, -1, axis=1)
        self.target_pos_data[:,-1] = target_pos

        self.actual_pos_data = np.roll(self.actual_pos_data, -1, axis=1)
        self.actual_pos_data[:,-1] = actual_pos

        self.time += self.cycle

        for i in range(6):
            self.pos_plot.setXRange(self.time[0],self.time[-1])
            self.target_pos_curves[i].setData(self.target_pos_data[i])
            self.actual_pos_curves[i].setData(self.actual_pos_data[i]) # Maybe need to add Transpose here
        
        self.force_data = np.roll(self.force_data, -1, axis=1)
        self.force_data[:,-1] = force
        self.force_plot.setXRange(self.time[0],self.time[-1])
        self.force_curve.setData(self.force_data.T)
        
        # QtWidgets.QApplication.processEvents()


class SingleAxisMonitor:
    def __init__(self):
        # self.app = pg.mkQApp()
        self.app = QtWidgets.QApplication(sys.argv)
        self.win = pg.GraphicsLayoutWidget(title="Single Axis Monitoring")
        
        self.pos_plot = self.win.addPlot(title="Position Tracking")
        self.pos_plot.addLegend()
        self.target_curve = self.pos_plot.plot(pen='r', name='Target Position')  
        self.actual_curve = self.pos_plot.plot(pen='g', name='Actual Position')   
        
        self.win.nextRow()
        self.force_plot = self.win.addPlot(title="Force Feedback")
        self.force_curve = self.force_plot.plot(pen='b')  
        
        self.buffer_size = 200
        self.cycle = 0.01
        self.time = np.linspace(-self.buffer_size*self.cycle, 0, self.buffer_size)  
        self.target_pos = np.zeros(self.buffer_size)
        self.actual_pos = np.zeros(self.buffer_size)
        self.z_force = np.zeros(self.buffer_size)
        
        self.pos_plot.setLabel('left', 'Position', 'mm')
        self.pos_plot.setLabel('bottom', 'Time', 's')
        self.force_plot.setLabel('left', 'Force', 'N')
        self.force_plot.setLabel('bottom', 'Time', 's')
        self.win.show()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        # self.timer.timeout.connect(self.update_data)
        self.timer.start(100)

        # store data
        self.data = []
        self.data_file_path = "data/monitor_data.csv"
        self.data_counter = 0
        self.data_interval = 10
    

    def update(self, target_z, actual_z, force_z):
        self.target_pos = np.roll(self.target_pos, -1)
        self.target_pos[-1] = target_z
        
        self.actual_pos = np.roll(self.actual_pos, -1)
        self.actual_pos[-1] = actual_z
        
        self.z_force = np.roll(self.z_force, -1)
        self.z_force[-1] = force_z
        
        self.time += self.cycle
        self.pos_plot.setXRange(self.time[0], self.time[-1])
        self.target_curve.setData(self.time, self.target_pos)
        self.actual_curve.setData(self.time, self.actual_pos)
        
        self.force_plot.setXRange(self.time[0], self.time[-1])
        self.force_curve.setData(self.time, self.z_force)

        self.data_counter += 1
        if self.data_counter >= self.data_interval:
            self.save_data()
            self.data_counter = 0
        
        # QtWidgets.QApplication.processEvents()
    def save_data(self):
        # Save current sample to in-memory list.
        self.data.append({
            "time": self.time[-1],
            "target_pos": self.target_pos[-1],
            "actual_pos": self.actual_pos[-1],
            "z_force": self.z_force[-1]
        })
        
        # Persist to file at fixed intervals.
        if len(self.data) >= 100:  # Save once every 100 samples.
            self.export_to_csv()

    def export_to_csv(self):
        # Ensure output directory exists.
        os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
        
        # Write CSV file.
        with open(self.data_file_path, 'w', newline='') as csvfile:
            fieldnames = ['time', 'target_pos', 'actual_pos', 'z_force']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in self.data:
                writer.writerow(row)
        
        print(f"Data exported to {self.data_file_path}")

    def close(self):
        # Export all buffered data on program exit.
        self.export_to_csv()
        self.win.close()
        self.app.quit()
    # def update_data(self):
        
    #     target_z = np.random.rand()  
    #     actual_z = np.random.rand()  
    #     force_z = np.random.rand()   
    #     self.update(target_z, actual_z, force_z)
