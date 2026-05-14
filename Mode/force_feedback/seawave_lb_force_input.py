import csv
from pathlib import Path

import numpy as np

from Mode.force_feedback._force_feedback_core import run_force_feedback_mode


def _lb_force_transform(force: np.ndarray) -> np.ndarray:
	# Keep sign convention consistent with other LB force modes.
	return -np.asarray(force, dtype=float)


def _load_wave_targets(wave_path: str) -> list[np.ndarray]:
	path_obj = Path(wave_path)
	if not path_obj.exists():
		raise FileNotFoundError(f"Wave file not found: {wave_path}")

	targets: list[np.ndarray] = []
	with path_obj.open("r", newline="", encoding="utf-8-sig") as f:
		reader = csv.reader(f)
		for row_index, row in enumerate(reader, start=1):
			if not row or all(not item.strip() for item in row):
				continue

			try:
				values = [float(item) for item in row]
			except ValueError as exc:
				raise ValueError(f"Invalid numeric value at line {row_index}: {row}") from exc

			if len(values) < 6:
				raise ValueError(
					f"Invalid wave row at line {row_index}: expected at least 6 values, got {len(values)}"
				)

			# Use first 6 columns as [rx, ry, rz, x, y, z].
			targets.append(np.asarray(values[:6], dtype=float))

	if not targets:
		raise ValueError(f"No valid wave trajectory rows found in: {wave_path}")

	return targets


class _CyclicWaveTargetProvider:
	def __init__(self, targets: list[np.ndarray]):
		self._targets = targets
		self._index = 0

	def next_target(self) -> np.ndarray:
		target = self._targets[self._index]
		self._index = (self._index + 1) % len(self._targets)
		return target


def run_mode(
	fixed_force: np.ndarray | list[float] | tuple[float, ...] | None = None,
	wave_path: str = "data/wave/example1.txt",
	use_force_sensor: bool = False,
	**kwargs,
) -> None:
	if fixed_force is None:
		raise ValueError("seawave_lb_force_input requires fixed_force with 6-axis values.")

	targets = _load_wave_targets(wave_path)
	provider = _CyclicWaveTargetProvider(targets)
	print(f"Loaded seawave trajectory: {wave_path}, rows={len(targets)}")
	print("Baseline motion is read row-by-row each control cycle and loops automatically.")

	run_force_feedback_mode(
		force_transform=_lb_force_transform,
		fixed_force=fixed_force,
		use_force_sensor=use_force_sensor,
		base_trajectory=provider.next_target,
		**kwargs,
	)


if __name__ == "__main__":
	run_mode(fixed_force=[0, 0, 10, 0, 0, 0])
