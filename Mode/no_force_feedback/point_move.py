from collections.abc import Sequence

from Controller.command_message import CommandCodes, CommandMessage
from Controller.dof_controller import DofController
from Controller.ip_setting import IpSetting
from Mode.platform_startup import ensure_platform_ready


def run_mode(
    target_dofs: Sequence[float] | None = None,
    speed: Sequence[float] | None = None,
) -> None:
    target = list(target_dofs) if target_dofs is not None else [0.0] * 6
    speed_array = list(speed) if speed is not None else None
    if len(target) != 6:
        raise ValueError("target_dofs must contain 6 values")
    if speed_array is not None and len(speed_array) != 6:
        raise ValueError("speed must contain 6 values when provided")

    controller = DofController(IpSetting())
    try:
        controller.connect()
        ensure_platform_ready(controller)
        command = CommandMessage(
            command_code=CommandCodes.ContinuousMoving,
            dofs=target,
            speed=speed_array,
        )
        controller.send_command(command)
        print(f"Point command sent. target_dofs={target}")
        print("Commands: 'get feedback' | 'set dofs' | 'exit'")

        while True:
            try:
                user_input = input(">> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting point_move mode.")
                break

            if user_input == "get feedback":
                feedback = controller.get_feedback()
                if feedback is not None:
                    print(f"feedback.AttitudesArray={feedback.AttitudesArray}")
                else:
                    print("No feedback received.")

            elif user_input == "set dofs":
                print("Enter 6 DOF values separated by spaces (pitch roll yaw lateral longitudinal vertical):")
                try:
                    raw = input("DOFs: ").strip()
                    new_dofs = list(map(float, raw.split()))
                    if len(new_dofs) != 6:
                        print(f"Expected 6 values, got {len(new_dofs)}. Ignored.")
                        continue
                    new_cmd = CommandMessage(
                        command_code=CommandCodes.ContinuousMoving,
                        dofs=new_dofs,
                        speed=speed_array,
                    )
                    controller.send_command(new_cmd)
                    target = new_dofs
                    print(f"New target sent: {target}")
                except ValueError:
                    print("Invalid input. Please enter numbers only.")

            elif user_input == "exit":
                print("Exiting point_move mode.")
                break

            else:
                print("Unknown command. Use: 'get feedback' | 'set dofs' | 'exit'")
    finally:
        controller.dispose()


if __name__ == "__main__":
    run_mode()