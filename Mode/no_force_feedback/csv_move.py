import csv
import time
from pathlib import Path

from Controller.command_message import CommandCodes, CommandMessage
from Controller.dof_controller import DofController
from Controller.ip_setting import IpSetting
from Mode.platform_startup import ensure_platform_ready

SCRIPT_INDEX_BINDINGS: dict[str, int] = {
	"data/wave/example1.txt": 1,
	"data/wave/example2.txt": 2,
	"data/wave/exmple2.txt": 2,
}


def _normalize_path_for_binding(path_obj: Path) -> str:
	return str(path_obj).replace("\\", "/").lower()


def _infer_script_index(script_path: Path) -> int | None:
	normalized = _normalize_path_for_binding(script_path)
	for key, value in SCRIPT_INDEX_BINDINGS.items():
		if normalized.endswith(key.lower()):
			return value
	return None


def _validate_script_file(script_path: Path) -> tuple[int, int]:
	valid_rows = 0
	reserved_zero_violations = 0
	nonzero_motion_rows = 0
	max_abs_motion = 0.0

	with script_path.open("r", newline="", encoding="utf-8-sig") as f:
		reader = csv.reader(f)
		for row_index, row in enumerate(reader, start=1):
			if not row or all(not value.strip() for value in row):
				continue
			if len(row) != 7:
				raise ValueError(
					f"Invalid script format at line {row_index}: expected 7 columns, got {len(row)}"
				)

			try:
				values = [float(value) for value in row]
			except ValueError as exc:
				raise ValueError(
					f"Invalid numeric value at line {row_index}: {row}"
				) from exc

			if abs(values[6]) > 1e-9:
				reserved_zero_violations += 1

			row_max_abs = max(abs(v) for v in values[:6])
			if row_max_abs > 1e-9:
				nonzero_motion_rows += 1
			if row_max_abs > max_abs_motion:
				max_abs_motion = row_max_abs

			valid_rows += 1

	if valid_rows == 0:
		raise ValueError(f"No valid 7-column script rows found in file: {script_path}")

	if nonzero_motion_rows == 0:
		print(
			f"Warning: script appears to be all zeros (file={script_path}). "
			"Platform motion will stay near origin."
		)
	else:
		print(
			f"Script analysis: nonzero_rows={nonzero_motion_rows}/{valid_rows}, "
			f"max_abs_motion={max_abs_motion:.6f}"
		)

	return valid_rows, reserved_zero_violations


def _resolve_script_path(script_path: str) -> Path:
	path_obj = Path(script_path)
	if path_obj.exists():
		return path_obj

	# Compatibility fallback: repository may store "exmple2.txt" (missing "a").
	if path_obj.name.lower() == "example2.txt":
		fallback = path_obj.with_name("exmple2.txt")
		if fallback.exists():
			return fallback

	return path_obj


def run_mode(
	script_file_index: int | None = None,
	script_path: str = "data/wave/example1.txt",
	monitor_seconds: float = 0.0,
	feedback_interval: float = 0.2,
) -> None:
	path_obj = _resolve_script_path(script_path)
	if not path_obj.exists():
		raise FileNotFoundError(f"Script file not found: {script_path}")

	mapped_index = _infer_script_index(path_obj)
	if script_file_index is None:
		if mapped_index is None:
			raise ValueError(
				"Cannot infer script_file_index from path. "
				"Please pass --script-index explicitly, or add path->index into SCRIPT_INDEX_BINDINGS "
				"in Mode/no_force_feedback/csv_move.py"
			)
		script_file_index = mapped_index
		print(f"Auto-bound script index: {script_path} -> {script_file_index}")

	if script_file_index < 0 or script_file_index > 255:
		raise ValueError("script_file_index must be in range [0, 255]")

	if mapped_index is not None and mapped_index != script_file_index:
		print(
			f"Warning: path mapping suggests index={mapped_index}, "
			f"but script_file_index={script_file_index} was provided."
		)

	row_count, reserved_mismatch_count = _validate_script_file(path_obj)
	if reserved_mismatch_count > 0:
		print(
			f"Warning: {reserved_mismatch_count} rows have non-zero reserved column in {script_path}"
		)

	controller = DofController(IpSetting())
	try:
		controller.connect()
		ensure_platform_ready(controller)
		command = CommandMessage(
			command_code=CommandCodes.WorkingWithScript,
			script_file_index=script_file_index,
		)
		print(
			f"Note: csv file is only validated locally ({path_obj}); "
			"controller executes by script_file_index on firmware side."
		)
		controller.send_command(command)
		print(
			f"WorkingWithScript command sent. script_file_index={script_file_index}, "
			f"validated_rows={row_count}"
		)

		if monitor_seconds <= 0:
			print("Script mode running. Press Ctrl+C to stop.")
			while True:
				feedback = controller.get_feedback()
				if feedback is not None:
					print(f"status={feedback.DOFStatus.name}, attitudes={feedback.AttitudesArray}")
				time.sleep(max(0.0, feedback_interval))
			return

		deadline = time.time() + monitor_seconds
		while time.time() < deadline:
			feedback = controller.get_feedback()
			if feedback is not None:
				print(f"status={feedback.DOFStatus.name}, attitudes={feedback.AttitudesArray}")
			time.sleep(max(0.0, feedback_interval))
	except KeyboardInterrupt:
		print("\nScript mode stopped by user.")
	finally:
		controller.dispose()


if __name__ == "__main__":
	run_mode()
