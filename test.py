class ControlSystem:
    def __init__(self):
        ip_setting =IpSetting()
        self.robot = DofController(ip_setting)
        self.force_sensor = ATIMini85()
        M = np.diag([1]*6)
        D = np.diag([5]*6)
        K = np.diag([100]*6)
        self.control_algorithm = ControlAlgorithm(M, D, K, CONTROL_CYCLE)

        # share data between threads
        self.force_queue = Queue()
        self.position_queue = Queue()
        # Synchronous event
        self.force_event = threading.Event()
        self.position_event = threading.Event()
        self.force_thread = None
        self.control_thread = None
        self.exit_event = threading.Event()
        self.is_running = False

        self.last_avg = np.zeros(6)
        # init filter
        self.filter_window = 10
        self.filter_buffer = np.zeros((self.filter_window,6))
    
    def force_acquisition(self):
        # Force data acquisition thread: read data from sensor and put into queue
        self.force_sensor.start(sampling_rate=FORCE_SAMPLE_RATE)
        self.force_sensor.calibrate_zero()
        try:
            while not self.exit_event.is_set():
                forces = self.force_sensor.get_calibrated_forces(num_samples=SAMPLE_CHUNK) # forces shape: [SAMPLE_CHUNK, 6 channels]
                # forces[:3], forces[3:] = forces[3:], forces[:3]
                if forces.shape[0] != SAMPLE_CHUNK or forces.shape[1] != 6:
                    print(f"Warning: Unexpected forces shape: {forces.shape}. Expected shape: ({SAMPLE_CHUNK}, 6)")
                else:
                    forces[:,:3], forces[:,3:] = forces[:,3:], forces[:,:3]
                # 1. slide average filter
                # if len(self.filter_buffer) >= self.filter_window:
                #     self.filter_buffer.pop(0)
                # self.filter_buffer.append(forces)
                # averaged_forces = np.mean(self.filter_buffer, axis=0)[-1]
                # real time low pass
                # current_avg = np.mean(forces, axis=0)
                # averaged_forces = 0.2*current_avg + 0.8*self.last_avg  # TODO: change the paramete coefficient
                # self.last_avg = averaged_forces

                if not self.force_queue.full():
                    # self.force_queue.put(averaged_forces) # forces[-1] Get the newest sample TODO: maybe use the average of the last 10 samples to avoid noise
                    self.force_queue.put(forces[-1])
                    self.force_event.set()
                else:
                    print("Warning: Force data queue is full. Force data may be lost.")
                time.sleep(FORCE_SAMPLE_CYCLE) # Small sleep to prevent CPU overload
        finally:
            self.force_sensor.stop()
            print("Force sensor acquisition thread stopped!")

    def control_loop(self):
        # Main Control Thread
        self.robot.connect() # Connect to the platform controller
        last_control_time = time.time()
        # self.initialize_csv()

        try:
            while not self.exit_event.is_set():
                # Synchronous control cycle
                current_time = time.time()
                # if (current_time - last_control_time)>=CONTROL_CYCLE:
                if current_time >= last_control_time:
                    # Get current pos and force
                    feedback = self.robot.get_feedback()
                    current_pos = feedback.AttitudesArray
                    a=self.force_queue.empty()
                    if not self.force_event.is_set():
                        self.force_event.wait()
                    F_e = self.force_queue.get()
                    F_e = -F_e
                    F_e[3:6]=0
                    # F_e[0]=2
                    # F_e[2]=2
                    # for i in range(6):
                    #     if -2<F_e[i]<2:
                    #         F_e[i] = 0
                    # F_e = self.force_queue.get() if not self.force_queue.empty() else np.zeros(6) # Get the latest force data from the queue
                    # F_e = [0, 0, 0, 0, 0, -10] # Test Step1: keep the Fz constant
                    # F_e[0:4] = 0 # Test Step2: only keep the z=axis force TODO: remember to remove this line 
                    # F_e[5] = 0

                    # Excute the control algorithm
                    target_pos = self.control_algorithm.update(F_e,current_pos)

                    self.force_event.clear()

                    # Send command to the platform
                    command = CommandMessage(
                        command_code=CommandCodes.ContinuousMoving,         # 9
                        dofs = target_pos # dofs TODO: Control algorithm output
                    )
                    # command_bytes = command.to_bytes()
                    # print(f"Command bytes: {command_bytes}")
                    self.robot.send_command(command)

                    # self.monitor.update(target_pos,current_pos,F_e) # TODO: Maybe need to remove 6axis monitor
                    # self.single_axis_monitor.update(target_pos[5],current_pos[5],F_e[5]) # Z-axis monitor
                    last_control_time += CONTROL_CYCLE
                    if last_control_time<current_time:
                        last_control_time = current_time+ CONTROL_CYCLE
                    # update the last control time
                    # last_control_time = current_time
                else:
                    time.sleep(max(0, last_control_time - current_time - 0.001))
        finally:
            # if self.csv_file is not None:
            #     self.csv_file.close()
            self.robot.dispose()
            print("Control loop thread stopped!")

    def start(self):

        self.force_thread = threading.Thread(target=self.force_acquisition, daemon=True)
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)

        self.force_thread.start()
        time.sleep(0.1)
        self.control_thread.start()

    def stop(self):
        # Stop the control system
        self.exit_event.set()
        self.force_thread.join()
        self.control_thread.join()