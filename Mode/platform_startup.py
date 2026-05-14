import time

from Controller.command_message import CommandCodes, CommandMessage
from Controller.dof_controller import DofController
from Controller.feedback_message import StatusCodes

_READY_STATUSES = {
    StatusCodes.MoveFromBottomToMiddleCompleted,
    StatusCodes.Moving,
    StatusCodes.CommandMoving,
    StatusCodes.RunningScript,
}

_FIND_BOTTOM_DONE_STATUSES = {
    StatusCodes.MoveToBottomCompleted,
}


def _wait_for_status(
    controller: DofController,
    expected_status: StatusCodes,
    timeout_seconds: float,
) -> None:
    _wait_for_any_status(controller, {expected_status}, timeout_seconds)


def _wait_for_any_status(
    controller: DofController,
    expected_statuses: set[StatusCodes],
    timeout_seconds: float,
) -> StatusCodes:
    deadline = time.time() + timeout_seconds
    last_status: StatusCodes | None = None

    while time.time() < deadline:
        feedback = controller.get_feedback()
        if feedback is None:
            continue

        status = feedback.DOFStatus
        last_status = status
        if status in expected_statuses:
            return status

    status_name = last_status.name if last_status is not None else "None"
    expected_names = "/".join(sorted(s.name for s in expected_statuses))
    raise TimeoutError(
        f"Timeout waiting for status {expected_names}. Last status: {status_name}"
    )


def ensure_platform_ready(
    controller: DofController,
    timeout_per_stage: float = 60.0,
    skip_if_ready: bool = True,
) -> None:
    if timeout_per_stage <= 0:
        raise ValueError("timeout_per_stage must be positive")

    if skip_if_ready:
        feedback = controller.get_feedback()
        if feedback is not None and feedback.DOFStatus in _READY_STATUSES:
            print(f"Platform already ready (status={feedback.DOFStatus.name}), skip 4/6 init.")
            return

    print("Startup sequence: send command 4 (FindBottomInitialize)")
    controller.send_command(
        CommandMessage(command_code=CommandCodes.FindBottomInitialize)
    )
    stage1_status = _wait_for_any_status(
        controller,
        _FIND_BOTTOM_DONE_STATUSES,
        timeout_per_stage,
    )
    print(f"Startup stage 1 completed: status={stage1_status.name}")

    print("Startup sequence: send command 6 (MoveFromBottomToMiddle)")
    controller.send_command(
        CommandMessage(command_code=CommandCodes.MoveFromBottomToMiddle)
    )
    _wait_for_status(
        controller,
        StatusCodes.MoveFromBottomToMiddleCompleted,
        timeout_per_stage,
    )

    print("Startup sequence completed: status reached MoveFromBottomToMiddleCompleted")
