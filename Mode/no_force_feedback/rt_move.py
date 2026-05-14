import threading
import time
import csv
import math
import queue
from pathlib import Path

from Controller.command_message import CommandCodes, CommandMessage, SubCommandCodes
from Controller.dof_controller import DofController
from Controller.ip_setting import IpSetting
from Mode.platform_startup import ensure_platform_ready

try:
	import msvcrt
except ImportError:  # pragma: no cover
	msvcrt = None


DEFAULT_RT_PATH = "data/wave/ocean_waves_extract.txt"

# If needed, change this constant for repeated execution.
LOOP_SEQUENCE = False


class FeedbackLogger:
	def __init__(self, path: Path):
		self._queue: queue.Queue = queue.Queue(maxsize=2048)
		self._file = path.open("w", newline="", encoding="utf-8")
		self._writer = csv.writer(self._file)
		self._writer.writerow(
			[
				"time_s",
				"cmd_x",
				"cmd_y",
				"cmd_z",
				"cmd_roll",
				"cmd_pitch",
				"cmd_yaw",
				"fb_x",
				"fb_y",
				"fb_z",
				"fb_roll",
				"fb_pitch",
				"fb_yaw",
			]
		)
		self._thread = threading.Thread(target=self._writer_loop, daemon=True)
		self._thread.start()

	def log(self, row: list[float]) -> None:
		try:
			self._queue.put_nowait(row)
		except queue.Full:
			print("Warning: feedback log queue full; dropping a record")

	def close(self) -> None:
		self._queue.put(None)
		self._thread.join(timeout=1.0)
		self._file.close()

	def _writer_loop(self) -> None:
		while True:
			item = self._queue.get()
			if item is None:
				break
			self._writer.writerow(item)
			self._file.flush()


class FeedbackMonitor:
	def __init__(self, controller, stop_event: threading.Event):
		self._controller = controller
		self._stop_event = stop_event
		self._lock = threading.Lock()
		self._latest = None
		self._thread = threading.Thread(target=self._monitor_loop, daemon=True)

	def start(self) -> None:
		self._thread.start()

	def latest(self):
		with self._lock:
			return self._latest

	def join(self, timeout: float = 0.5) -> None:
		self._thread.join(timeout=timeout)

	def _monitor_loop(self) -> None:
		while not self._stop_event.is_set():
			feedback = self._controller.get_feedback()
			if feedback is not None:
				with self._lock:
					self._latest = feedback


def _resolve_position_path(position_path: str) -> Path:
	path_obj = Path(position_path)
	if path_obj.is_absolute():
		return path_obj

	repo_root = Path(__file__).resolve().parents[2]
	return repo_root / path_obj


def _load_target_positions(position_path: str) -> list[list[float]]:
	path_obj = _resolve_position_path(position_path)
	if not path_obj.exists():
		raise FileNotFoundError(f"RT move file not found: {position_path}")

	positions: list[list[float]] = []
	with path_obj.open("r", newline="", encoding="utf-8-sig") as csv_file:
		reader = csv.reader(csv_file)
		for row_index, row in enumerate(reader, start=1):
			if not row or all(not value.strip() for value in row):
				continue

			if len(row) not in (6, 7):
				raise ValueError(
					f"Invalid RT move format at line {row_index}: expected 6 or 7 columns, got {len(row)}"
				)

			try:
				values = [float(value) for value in row]
			except ValueError as exc:
				raise ValueError(f"Invalid numeric value at line {row_index}: {row}") from exc

			# Extract first 6 columns: [rx, ry, rz, x_mm, y_mm, z_mm]
			# Column 7 is reserved and ignored
			dofs = values[:6]
			# Convert xyz from mm to m (divide by 1000)
			dofs[3] /= 1000.0  # x: mm -> m
			dofs[4] /= 1000.0  # y: mm -> m
			dofs[5] /= 1000.0  # z: mm -> m
			positions.append(dofs)

	if not positions:
		raise ValueError(f"No valid target positions found in file: {position_path}")

	print(f"Loaded {len(positions)} target positions from {path_obj}")
	return positions


def _keyboard_control_worker(
	stop_event: threading.Event,
	state: dict[str, bool],
	enable_control: bool,
) -> None:
	if not enable_control or msvcrt is None:
		return

	print("Keyboard control enabled: Space=pause/resume, Q=quit")
	while not stop_event.is_set():
		if not msvcrt.kbhit():
			time.sleep(0.02)
			continue

		key = msvcrt.getwch().lower()
		if key == "q":
			print("Stop requested by keyboard (Q).")
			stop_event.set()
			return

		if key == " ":
			state["paused"] = not state["paused"]
			print("Paused." if state["paused"] else "Resumed.")
			continue


def run_mode(position_interval: float = 0.1, position_path: str = DEFAULT_RT_PATH) -> None:
	if position_interval <= 0:
		raise ValueError("position_interval must be positive")

	positions = _load_target_positions(position_path)
	for index, dofs in enumerate(positions):
		if len(dofs) != 6:
			raise ValueError(f"Target position at index {index} must contain 6 values")

	controller = DofController(IpSetting())
	stop_event = threading.Event()
	state = {"paused": False}

	keyboard_thread = threading.Thread(
		target=_keyboard_control_worker,
		args=(stop_event, state, True),
		daemon=True,
	)

	logger = None
	feedback_monitor = None
	try:
		controller.connect()
		ensure_platform_ready(controller)

		feedback_dir = Path(__file__).resolve().parents[2] / "feedback"
		feedback_dir.mkdir(parents=True, exist_ok=True)
		log_path = feedback_dir / f"{Path(position_path).stem}_rt_feedback_{int(time.time())}.csv"
		logger = FeedbackLogger(log_path)
		feedback_monitor = FeedbackMonitor(controller, stop_event)
		feedback_monitor.start()
		keyboard_thread.start()

		sequence_count = 0
		sequence_real_start = time.time()
		while not stop_event.is_set():
			sequence_count += 1
			print(f"Running position sequence #{sequence_count} ({len(positions)} points)")
			
			# Record the start time for this sequence to enable absolute timing
			sequence_start_time = time.monotonic()
			total_pause_duration = 0.0

			for point_index, dofs in enumerate(positions, start=1):
				if stop_event.is_set():
					break

				# Handle pause/resume, tracking accumulated pause duration
				pause_start_time = None
				while state["paused"] and not stop_event.is_set():
					if pause_start_time is None:
						pause_start_time = time.monotonic()
					time.sleep(0.05)

				if pause_start_time is not None:
					total_pause_duration += time.monotonic() - pause_start_time

				# Calculate the scheduled send time for this point using absolute timing
				# This accounts for command execution time and prevents drift
				scheduled_time = sequence_start_time + (point_index - 1) * position_interval + total_pause_duration

				command = CommandMessage(
					command_code=CommandCodes.CommandMoving,
					sub_command_code=SubCommandCodes.Step,
					dofs=dofs,
				)
				controller.send_command(command)
				print(f"Sent point {point_index}: {dofs}")

				feedback = feedback_monitor.latest() if feedback_monitor is not None else None
				if feedback is None:
					fb_values = [math.nan] * 6
					print(f"Warning: no feedback available for point {point_index}, recording NaN values")
				else:
					fb_values = list(feedback.AttitudesArray[:6])

				command_values = [
					dofs[3],
					dofs[4],
					dofs[5],
					dofs[0],
					dofs[1],
					dofs[2],
				]
				feedback_record = [
					fb_values[3],
					fb_values[4],
					fb_values[5],
					fb_values[0],
					fb_values[1],
					fb_values[2],
				]
				logger.log([
					time.time() - sequence_real_start,
					*command_values,
					*feedback_record,
				])

				current_time = time.monotonic()
				time_until_next = scheduled_time - current_time
				if time_until_next > 0:
					time.sleep(time_until_next)

			if not LOOP_SEQUENCE:
				break
	finally:
		stop_event.set()
		if keyboard_thread.is_alive():
			keyboard_thread.join(timeout=0.2)
		if feedback_monitor is not None:
			feedback_monitor.join(timeout=0.5)
		if logger is not None:
			logger.close()
		controller.dispose()
		stop_event.set()
		if keyboard_thread.is_alive():
			keyboard_thread.join(timeout=0.2)
		controller.dispose()


if __name__ == "__main__":
	run_mode()
