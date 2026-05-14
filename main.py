import argparse
from ast import literal_eval
from typing import Any

from Mode import list_modes, run_mode

DEFAULT_MODE = "point_move"


def _parse_vector_arg(raw_value: str | None, arg_name: str, required: bool = False) -> list[float] | None:
    # Parse scalar or 6-axis vector from CLI string argument.
    if raw_value is None:
        if required:
            raise ValueError(f"--{arg_name} is required for this mode.")
        return None

    text = raw_value.strip()
    if not text:
        if required:
            raise ValueError(f"--{arg_name} cannot be empty.")
        return None

    parsed: Any
    try:
        # Supports forms like "[1,2,3,4,5,6]" or "2".
        parsed = literal_eval(text)
        data = list(parsed) if isinstance(parsed, (list, tuple)) else [float(parsed)]
    except (ValueError, SyntaxError):
        # Fallback for plain comma-separated input like "1,2,3,4,5,6".
        data = [float(part.strip()) for part in text.split(",") if part.strip()]

    if len(data) == 1:
        # Broadcast one scalar to all six axes.
        return [float(data[0])] * 6

    if len(data) != 6:
        raise ValueError(f"--{arg_name} must contain 6 values or a single scalar value.")

    return [float(v) for v in data]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Force control mode runner")
    parser.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        choices=list_modes(),
        help="Mode name to run",
    )

    parser.add_argument(
        "--csv-path",
        default="data/wave/example2.txt",
        help="Script file path for csv_move format validation",
    )
    parser.add_argument(
        "--script-index",
        type=int,
        default=None,
        help="Internal script index for WorkingWithScript mode (optional)",
    )
    parser.add_argument(
        "--script-monitor",
        type=float,
        default=0.0,
        help="Feedback monitor seconds after sending WorkingWithScript command",
    )

    parser.add_argument(
        "--rt-interval",
        type=float,
        default=0.1,
        help="Time interval between two rt_move target positions",
    )
    parser.add_argument(
        "--rt-path",
        type=str,
        default="data/wave/example1.txt",
        help="Position file path for rt_move (.txt/.csv), default data/wave/example1.txt",
    )

    parser.add_argument(
        "--point-dofs",
        type=float,
        nargs=6,
        metavar=("DOF1", "DOF2", "DOF3", "DOF4", "DOF5", "DOF6"),
        help="Target DOFs for point_move mode",
    )
    parser.add_argument(
        "--point-speed",
        type=float,
        nargs=6,
        metavar=("S1", "S2", "S3", "S4", "S5", "S6"),
        help="Optional speed array for point_move mode",
    )

    parser.add_argument(
        "--sin-amplitude",
        type=float,
        nargs=6,
        metavar=("A1", "A2", "A3", "A4", "A5", "A6"),
        help="Amplitude array for sin_move mode",
    )
    parser.add_argument(
        "--sin-frequency",
        type=float,
        nargs=6,
        metavar=("F1", "F2", "F3", "F4", "F5", "F6"),
        help="Frequency array for sin_move mode",
    )
    parser.add_argument(
        "--sin-phase",
        type=float,
        nargs=6,
        metavar=("P1", "P2", "P3", "P4", "P5", "P6"),
        help="Phase array for sin_move mode",
    )
    parser.add_argument(
        "--sin-monitor",
        type=float,
        default=0.0,
        help="Feedback monitor seconds for sin_move mode",
    )

    parser.add_argument(
        "--force-fixed",
        type=str,
        default=None,
        help="Fixed 6-axis force for steady_lb_force_input, e.g. [0,0,10,0,0,0]",
    )
    parser.add_argument(
        "--force-use-sensor",
        action="store_true",
        help="Connect force sensor before control (optional for steady_lb_force_input)",
    )
    parser.add_argument(
        "--force-axes",
        type=str,
        default=None,
        help="6-axis enable mask, e.g. [1,1,1,1,1,1]",
    )
    parser.add_argument(
        "--force-m",
        type=str,
        default=None,
        help="M diag, scalar or 6 values",
    )
    parser.add_argument(
        "--force-d",
        type=str,
        default=None,
        help="D diag, scalar or 6 values",
    )
    parser.add_argument(
        "--force-k",
        type=str,
        default=None,
        help="K diag, scalar or 6 values",
    )
    parser.add_argument(
        "--wave-path",
        type=str,
        default="data/wave/example1.txt",
        help="Wave baseline file for seawave modes (.txt/.csv), default data/wave/example1.txt",
    )

    return parser


def build_mode_kwargs(args: argparse.Namespace) -> dict:
    if args.mode == "csv_move":
        return {
            "script_file_index": args.script_index,
            "script_path": args.csv_path,
            "monitor_seconds": args.script_monitor,
        }

    if args.mode == "rt_move":
        return {
            "position_interval": args.rt_interval,
            "position_path": args.rt_path,
        }

    if args.mode == "point_move":
        return {
            "target_dofs": args.point_dofs,
            "speed": args.point_speed,
        }

    if args.mode == "sin_move":
        return {
            "amplitude_array": args.sin_amplitude,
            "frequency_array": args.sin_frequency,
            "phase_array": args.sin_phase,
            "monitor_seconds": args.sin_monitor,
        }

    if args.mode == "steady_lb_force_input":
        # LB mode requires explicit fixed force input.
        return {
            "fixed_force": _parse_vector_arg(args.force_fixed, "force-fixed", required=True),
            "use_force_sensor": args.force_use_sensor,
            "enabled_axes": _parse_vector_arg(args.force_axes, "force-axes", required=False),
            "m_diag": _parse_vector_arg(args.force_m, "force-m", required=False),
            "d_diag": _parse_vector_arg(args.force_d, "force-d", required=False),
            "k_diag": _parse_vector_arg(args.force_k, "force-k", required=False),
        }

    if args.mode == "steady_arbitary_force_input":
        # Arbitrary mode ignores --force-fixed and always uses live sensor forces.
        return {
            "enabled_axes": _parse_vector_arg(args.force_axes, "force-axes", required=False),
            "m_diag": _parse_vector_arg(args.force_m, "force-m", required=False),
            "d_diag": _parse_vector_arg(args.force_d, "force-d", required=False),
            "k_diag": _parse_vector_arg(args.force_k, "force-k", required=False),
        }

    if args.mode == "seawave_arbitray_force_input":
        return {
            "wave_path": args.wave_path,
            "enabled_axes": _parse_vector_arg(args.force_axes, "force-axes", required=False),
            "m_diag": _parse_vector_arg(args.force_m, "force-m", required=False),
            "d_diag": _parse_vector_arg(args.force_d, "force-d", required=False),
            "k_diag": _parse_vector_arg(args.force_k, "force-k", required=False),
        }

    if args.mode == "seawave_lb_force_input":
        return {
            "wave_path": args.wave_path,
            "fixed_force": _parse_vector_arg(args.force_fixed, "force-fixed", required=True),
            "use_force_sensor": args.force_use_sensor,
            "enabled_axes": _parse_vector_arg(args.force_axes, "force-axes", required=False),
            "m_diag": _parse_vector_arg(args.force_m, "force-m", required=False),
            "d_diag": _parse_vector_arg(args.force_d, "force-d", required=False),
            "k_diag": _parse_vector_arg(args.force_k, "force-k", required=False),
        }

    return {}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    mode_kwargs = build_mode_kwargs(args)
    run_mode(args.mode, **mode_kwargs)


if __name__ == "__main__":
    main()
