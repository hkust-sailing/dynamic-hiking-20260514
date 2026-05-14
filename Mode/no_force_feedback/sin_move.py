import time
import math
from collections.abc import Sequence

from Controller.command_message import CommandCodes, CommandMessage, SubCommandCodes
from Controller.dof_controller import DofController
from Controller.feedback_message import StatusCodes
from Controller.ip_setting import IpSetting
from Mode.platform_startup import ensure_platform_ready


def _monitor_feedback(
	controller: DofController,
	monitor_seconds: float,
	feedback_interval: float,
) -> None:
	if monitor_seconds <= 0:
		print("Sine mode running. Press Ctrl+C to stop.")
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


def _run_software_sine_fallback(
	controller: DofController,
	amplitude: list[float],
	frequency: list[float],
	phase: list[float],
	monitor_seconds: float,
	feedback_interval: float,
	send_interval: float = 0.02,
) -> None:
	base = [0.0] * 6
	feedback = controller.get_feedback()
	if feedback is not None:
		base = list(feedback.AttitudesArray)

	print("Firmware sine mode not activated, fallback to software sine streaming (ContinuousMoving).")
	print(f"software-sine base={base}")

	start = time.time()
	next_send = start
	next_feedback = start

	while True:
		now = time.time()
		elapsed = now - start

		if monitor_seconds > 0 and elapsed >= monitor_seconds:
			break

		if now >= next_send:
			target = [
				base[i] + amplitude[i] * math.sin(2.0 * math.pi * frequency[i] * elapsed + phase[i])
				for i in range(6)
			]
			controller.send_command(
				CommandMessage(
					command_code=CommandCodes.ContinuousMoving,
					dofs=target,
				)
			)
			next_send += send_interval
			if next_send < now:
				next_send = now + send_interval

		if now >= next_feedback:
			feedback = controller.get_feedback()
			if feedback is not None:
				print(f"status={feedback.DOFStatus.name}, attitudes={feedback.AttitudesArray}")
			next_feedback = now + max(0.05, feedback_interval)

		time.sleep(0.002)


def run_mode(
	amplitude_array: Sequence[float] | None = None,
	frequency_array: Sequence[float] | None = None,
	phase_array: Sequence[float] | None = None,
	monitor_seconds: float = 0.0,
	feedback_interval: float = 0.5,
) -> None:
	amplitude = list(amplitude_array) if amplitude_array is not None else [0.0] * 6
	frequency = list(frequency_array) if frequency_array is not None else [0.1] * 6
	phase = list(phase_array) if phase_array is not None else [0.0] * 6

	if len(amplitude) != 6 or len(frequency) != 6 or len(phase) != 6:
		raise ValueError("amplitude_array/frequency_array/phase_array must all contain 6 values")

	controller = DofController(IpSetting())
	try:
		controller.connect()
		ensure_platform_ready(controller)

		command = CommandMessage(
			command_code=CommandCodes.CommandMoving,
			sub_command_code=SubCommandCodes.SineWave,
			amplitude_array=amplitude,
			frequency_array=frequency,
			phase_array=phase,
		)
		controller.send_command(command)
		print("Sine command sent.")
		print(f"amplitude={amplitude}")
		print(f"frequency={frequency}")
		print(f"phase={phase}")

		hardware_sine_activated = False
		activation_deadline = time.time() + 2.0
		while time.time() < activation_deadline:
			feedback = controller.get_feedback()
			if feedback is not None:
				if feedback.DOFStatus == StatusCodes.CommandMoving:
					hardware_sine_activated = True
					break

		if hardware_sine_activated:
			print("Hardware sine mode activated (status=CommandMoving).")
			_monitor_feedback(controller, monitor_seconds, feedback_interval)
		else:
			_run_software_sine_fallback(
				controller,
				amplitude=amplitude,
				frequency=frequency,
				phase=phase,
				monitor_seconds=monitor_seconds,
				feedback_interval=feedback_interval,
			)
	except KeyboardInterrupt:
		print("\nSine mode stopped by user.")
	finally:
		controller.dispose()


if __name__ == "__main__":
	run_mode()
