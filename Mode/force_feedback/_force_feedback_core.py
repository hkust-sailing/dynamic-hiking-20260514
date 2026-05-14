import threading
import time
from queue import Queue
from typing import Callable

import numpy as np

from Controller.command_message import CommandCodes, CommandMessage
from Controller.dof_controller import DofController
from Controller.ip_setting import IpSetting
from ForceSensor.ati_mini85 import ATIMini85
from ForceSensor.control_algorithm import ControlAlgorithm
from Mode.platform_startup import ensure_platform_ready

# Main control-loop period in seconds.
# 0.01 s means the controller updates at 100 Hz.
DEFAULT_CONTROL_CYCLE = 0.01
# Force-sensor sampling rate in Hz (samples per second).
DEFAULT_FORCE_SAMPLE_RATE = 100
# Number of raw samples read from the force sensor in one acquisition call.
# Value 1 means "single latest sample" mode.
DEFAULT_SAMPLE_CHUNK = 1
DEFAULT_M_DIAG = np.array([2, 100, 100, 500, 500, 2], dtype=float)
DEFAULT_D_DIAG = np.array([2.3, 100, 100, 500, 500, 16], dtype=float)
DEFAULT_K_DIAG = np.array([10, 100, 100, 500, 500, 100], dtype=float)
DEFAULT_ENABLED_AXES = np.ones(6, dtype=float)


def _normalize_vector6(value: np.ndarray | list[float] | tuple[float, ...], name: str) -> np.ndarray:
    # Accept either one scalar (broadcast to 6 axes) or an explicit 6-axis vector.
    arr = np.asarray(value, dtype=float)
    if arr.ndim == 0:
        return np.full(6, float(arr), dtype=float)

    arr = arr.reshape(-1)
    if arr.size != 6:
        raise ValueError(f"{name} must contain exactly 6 values, got {arr.size}.")
    return arr


class ForceFeedbackControlSystem:
    def __init__(
        self,
        force_transform: Callable[[np.ndarray], np.ndarray],
        control_cycle: float = DEFAULT_CONTROL_CYCLE,
        force_sample_rate: int = DEFAULT_FORCE_SAMPLE_RATE,
        sample_chunk: int = DEFAULT_SAMPLE_CHUNK,
        use_force_sensor: bool = True,
        fixed_force: np.ndarray | list[float] | tuple[float, ...] | None = None,
        enabled_axes: np.ndarray | list[float] | tuple[float, ...] | None = None,
        m_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
        d_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
        k_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
        base_trajectory: Callable[[], np.ndarray] | None = None,
    ):
        ip_setting = IpSetting()
        self.robot = DofController(ip_setting)
        self.use_force_sensor = use_force_sensor
        # Sensor object is created only when explicitly needed.
        self.force_sensor = ATIMini85() if use_force_sensor else None

        self.control_cycle = control_cycle
        self.force_sample_rate = force_sample_rate
        self.sample_chunk = sample_chunk
        self.force_transform = force_transform
        # Optional per-cycle base motion target (6 DOF) to be used as desired trajectory.
        # When None, desired trajectory stays at controller default (typically zeros).
        self.base_trajectory = base_trajectory
        # When fixed_force is provided, it overrides live sensor force in control loop.
        self.fixed_force = (
            _normalize_vector6(fixed_force, "fixed_force") if fixed_force is not None else None
        )
        # Axis mask: 1 means force control enabled on this axis, 0 means disabled.
        self.enabled_axes = (
            _normalize_vector6(enabled_axes, "enabled_axes")
            if enabled_axes is not None
            else DEFAULT_ENABLED_AXES.copy()
        )

        # MDK are diagonal-only by design in this mode.
        m = np.diag(_normalize_vector6(m_diag, "m_diag") if m_diag is not None else DEFAULT_M_DIAG)
        d = np.diag(_normalize_vector6(d_diag, "d_diag") if d_diag is not None else DEFAULT_D_DIAG)
        k = np.diag(_normalize_vector6(k_diag, "k_diag") if k_diag is not None else DEFAULT_K_DIAG)
        self.control_algorithm = ControlAlgorithm(m, d, k, control_cycle)

        self.force_queue: Queue[np.ndarray] = Queue(maxsize=max(1, force_sample_rate // 5))
        self.force_event = threading.Event()
        self.exit_event = threading.Event()

        self.force_thread: threading.Thread | None = None
        self.control_thread: threading.Thread | None = None

    def force_acquisition(self) -> None:
        # Guard for modes that intentionally skip hardware force acquisition.
        if not self.use_force_sensor or self.force_sensor is None:
            return

        self.force_sensor.start(sampling_rate=self.force_sample_rate)
        self.force_sensor.calibrate_zero()
        try:
            target_period = 1 / self.force_sample_rate
            while not self.exit_event.is_set():
                start = time.perf_counter()
                forces = self.force_sensor.get_calibrated_forces(num_samples=self.sample_chunk)
                if forces.shape[0] != self.sample_chunk or forces.shape[1] != 6:
                    print(
                        f"Warning: Unexpected forces shape: {forces.shape}. "
                        f"Expected shape: ({self.sample_chunk}, 6)"
                    )
                else:
                    # Align sensor channels with controller conventions.
                    tmp = forces.copy()
                    forces[:, :3] = tmp[:, 3:]
                    forces[:, 3:] = tmp[:, :3]

                    if self.force_queue.full():
                        # Keep queue fresh by dropping stale sample when full.
                        self.force_queue.get_nowait()

                    self.force_queue.put(forces[-1])
                    self.force_event.set()

                elapsed = time.perf_counter() - start
                time.sleep(max(0, target_period - elapsed))
        finally:
            self.force_sensor.stop()
            print("Force sensor acquisition thread stopped!")

    def control_loop(self) -> None:
        self.robot.connect()
        ensure_platform_ready(self.robot)
        last_control_time = time.time()

        try:
            while not self.exit_event.is_set():
                current_time = time.time()
                if current_time >= last_control_time:
                    feedback = self.robot.get_feedback()
                    if feedback is None:
                        last_control_time += self.control_cycle
                        continue

                    current_pos = feedback.AttitudesArray
                    measured_force = np.zeros(6, dtype=float)

                    if self.use_force_sensor:
                        if not self.force_event.is_set():
                            self.force_event.wait(timeout=self.control_cycle)

                        if self.force_queue.empty():
                            last_control_time += self.control_cycle
                            continue

                        while self.force_queue.qsize() > 1:
                            # Only keep latest sample to avoid delayed control response.
                            self.force_queue.get_nowait()

                        measured_force = self.force_queue.get()

                    # Force source priority: fixed_force > measured sensor force.
                    source_force = self.fixed_force if self.fixed_force is not None else measured_force

                    if self.base_trajectory is not None:
                        base_target = np.asarray(self.base_trajectory(), dtype=float)
                        if base_target.shape != (6,):
                            raise ValueError(
                                f"base_trajectory output must be shape (6,), got {base_target.shape}."
                            )
                        # Base target is treated as [rx, ry, rz, x, y, z] with rotational terms in degree.
                        self.control_algorithm.set_desired_trajectory(base_target, deg_input=True)

                    force_error = np.asarray(self.force_transform(source_force), dtype=float)
                    if force_error.shape != (6,):
                        raise ValueError(
                            f"force_transform output must be shape (6,), got {force_error.shape}."
                        )
                    # Apply per-axis enable mask after transformation.
                    force_error = force_error * self.enabled_axes
                    target_pos = self.control_algorithm.update(force_error, current_pos)
                    if self.use_force_sensor:
                        self.force_event.clear()

                    command = CommandMessage(
                        command_code=CommandCodes.ContinuousMoving,
                        dofs=target_pos,
                    )
                    self.robot.send_command(command)

                    last_control_time += self.control_cycle
                    if last_control_time < current_time:
                        last_control_time = current_time + self.control_cycle
                else:
                    time.sleep(max(0, last_control_time - current_time - 0.001))
        finally:
            self.robot.dispose()
            print("Control loop thread stopped!")

    def start(self) -> None:
        if self.use_force_sensor:
            self.force_thread = threading.Thread(target=self.force_acquisition, daemon=True)
            self.force_thread.start()
            # Small delay allows acquisition thread to produce first valid sample.
            time.sleep(0.1)
        else:
            self.force_thread = None

        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()

    def stop(self) -> None:
        self.exit_event.set()

        if self.force_thread is not None and self.force_thread.is_alive():
            self.force_thread.join()
        if self.control_thread is not None and self.control_thread.is_alive():
            self.control_thread.join()



def run_force_feedback_mode(
    force_transform: Callable[[np.ndarray], np.ndarray],
    control_cycle: float = DEFAULT_CONTROL_CYCLE,
    force_sample_rate: int = DEFAULT_FORCE_SAMPLE_RATE,
    sample_chunk: int = DEFAULT_SAMPLE_CHUNK,
    use_force_sensor: bool = True,
    fixed_force: np.ndarray | list[float] | tuple[float, ...] | None = None,
    enabled_axes: np.ndarray | list[float] | tuple[float, ...] | None = None,
    m_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
    d_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
    k_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
    base_trajectory: Callable[[], np.ndarray] | None = None,
) -> None:
    # This helper is shared by all force-feedback mode wrappers.
    system = ForceFeedbackControlSystem(
        force_transform=force_transform,
        control_cycle=control_cycle,
        force_sample_rate=force_sample_rate,
        sample_chunk=sample_chunk,
        use_force_sensor=use_force_sensor,
        fixed_force=fixed_force,
        enabled_axes=enabled_axes,
        m_diag=m_diag,
        d_diag=d_diag,
        k_diag=k_diag,
        base_trajectory=base_trajectory,
    )

    try:
        system.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        system.stop()
