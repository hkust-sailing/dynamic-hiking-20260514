import threading
import time
import csv
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

	try:
		controller.connect()
		ensure_platform_ready(controller)
		keyboard_thread.start()

		sequence_count = 0
		while not stop_event.is_set():
			sequence_count += 1
			print(f"Running position sequence #{sequence_count} ({len(positions)} points)")

			for point_index, dofs in enumerate(positions, start=1):
				if stop_event.is_set():
					break

				while state["paused"] and not stop_event.is_set():
					time.sleep(0.05)

				command = CommandMessage(
					command_code=CommandCodes.CommandMoving,
					sub_command_code=SubCommandCodes.Step,
					dofs=dofs,
				)
				controller.send_command(command)
				print(f"Sent point {point_index}: {dofs}")
				time.sleep(position_interval)

			if not LOOP_SEQUENCE:
				break
	finally:
		stop_event.set()
		if keyboard_thread.is_alive():
			keyboard_thread.join(timeout=0.2)
		controller.dispose()


if __name__ == "__main__":
	run_mode()
