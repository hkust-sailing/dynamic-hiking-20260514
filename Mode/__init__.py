from typing import Callable

from Mode.force_feedback.seawave_lb_force_input import run_mode as run_seawave_lb_force_input
from Mode.force_feedback.seawave_arbitray_force_input import run_mode as run_seawave_arbitray_force_input
from Mode.force_feedback.steady_arbitary_force_input import run_mode as run_steady_arbitary_force_input
from Mode.force_feedback.steady_lb_force_input import run_mode as run_steady_lb_force_input
from Mode.no_force_feedback.csv_move import run_mode as run_csv_move
from Mode.no_force_feedback.point_move import run_mode as run_point_move
from Mode.no_force_feedback.rt_move import run_mode as run_rt_move
from Mode.no_force_feedback.sin_move import run_mode as run_sin_move

MODE_REGISTRY: dict[str, Callable[..., None]] = {
    "steady_lb_force_input": run_steady_lb_force_input,
    "steady_arbitary_force_input": run_steady_arbitary_force_input,
    "seawave_arbitray_force_input": run_seawave_arbitray_force_input,
    "seawave_lb_force_input": run_seawave_lb_force_input,
    "point_move": run_point_move,
    "sin_move": run_sin_move,
    "rt_move": run_rt_move,
    "csv_move": run_csv_move,
}


def list_modes() -> list[str]:
    return sorted(MODE_REGISTRY.keys())


def run_mode(mode_name: str, **kwargs) -> None:
    if mode_name not in MODE_REGISTRY:
        available = ", ".join(list_modes())
        raise ValueError(f"Unknown mode '{mode_name}'. Available modes: {available}")
    MODE_REGISTRY[mode_name](**kwargs)
