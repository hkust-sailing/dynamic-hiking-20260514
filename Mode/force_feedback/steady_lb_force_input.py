import numpy as np
from ast import literal_eval

from Mode.force_feedback._force_feedback_core import run_force_feedback_mode


def _lb_force_transform(force: np.ndarray) -> np.ndarray:
    # Keep LB mode behavior consistent with existing convention (sign inversion only).
    return -np.asarray(force, dtype=float)


def _parse_vector6(raw_text: str, name: str) -> np.ndarray:
    # Accept either Python-list style input or comma-separated text from terminal input.
    text = raw_text.strip()
    if not text:
        raise ValueError(f"{name} cannot be empty.")

    try:
        parsed = literal_eval(text)
        arr = np.asarray(parsed, dtype=float)
    except (ValueError, SyntaxError):
        parts = [p.strip() for p in text.split(",") if p.strip()]
        arr = np.asarray([float(p) for p in parts], dtype=float)

    arr = arr.reshape(-1)
    if arr.size != 6:
        raise ValueError(f"{name} must contain 6 values, got {arr.size}.")
    return arr


def _parse_diag_input(raw_text: str, default_value: np.ndarray) -> np.ndarray:
    # Empty input means "use default" for that diagonal.
    text = raw_text.strip()
    if not text:
        return default_value.copy()

    try:
        parsed = literal_eval(text)
        arr = np.asarray(parsed, dtype=float)
    except (ValueError, SyntaxError):
        parts = [p.strip() for p in text.split(",") if p.strip()]
        arr = np.asarray([float(p) for p in parts], dtype=float)

    if arr.ndim == 0:
        # Scalar input is broadcast to all axes.
        return np.full(6, float(arr), dtype=float)

    arr = arr.reshape(-1)
    if arr.size != 6:
        raise ValueError(f"MDK axis settings must be a scalar or 6 values, got {arr.size}.")
    return arr


def run_mode(
    fixed_force: np.ndarray | list[float] | tuple[float, ...] | None = None,
    use_force_sensor: bool = False,
    enabled_axes: np.ndarray | list[float] | tuple[float, ...] | None = None,
    m_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
    d_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
    k_diag: np.ndarray | list[float] | tuple[float, ...] | float | None = None,
    **kwargs,
) -> None:
    if fixed_force is None:
        # LB mode always needs an explicit fixed target force vector.
        raise ValueError("steady_lb_force_input requires fixed_force with 6-axis values.")

    run_force_feedback_mode(
        force_transform=_lb_force_transform,
        fixed_force=fixed_force,
        use_force_sensor=use_force_sensor,
        enabled_axes=enabled_axes,
        m_diag=m_diag,
        d_diag=d_diag,
        k_diag=k_diag,
        **kwargs,
    )


if __name__ == "__main__":
    default_m = np.array([2, 100, 100, 500, 500, 2], dtype=float)
    default_d = np.array([2.3, 100, 100, 500, 500, 16], dtype=float)
    default_k = np.array([10, 100, 100, 500, 500, 100], dtype=float)
    default_axes = np.ones(6, dtype=float)

    use_defaults = input("Use default MDK and axis enable mask (all 1)? [Y/n]: ").strip().lower()
    keep_default = use_defaults in ("", "y", "yes")

    if keep_default:
        # Default path keeps previous tuning unchanged.
        m_diag = default_m
        d_diag = default_d
        k_diag = default_k
        enabled_axes = default_axes
    else:
        m_diag = _parse_diag_input(
            input("Input M diag (single value or 6 values, e.g. 2 or [2,2,2,2,2,2]): "),
            default_m,
        )
        d_diag = _parse_diag_input(
            input("Input D diag (single value or 6 values): "),
            default_d,
        )
        k_diag = _parse_diag_input(
            input("Input K diag (single value or 6 values): "),
            default_k,
        )
        enabled_axes = _parse_vector6(
            input("Input axis enable mask [a1,a2,a3,a4,a5,a6], 0=off, 1=on: "),
            "enabled_axes",
        )

    sensor_flag = input("Connect force sensor first? [y/N]: ").strip().lower()
    # In LB mode this only controls whether hardware is connected/read first.
    # The controller input still uses fixed_force when provided.
    use_force_sensor = sensor_flag in ("y", "yes")

    fixed_force = _parse_vector6(
        input("Input fixed 6-axis force [f1,f2,f3,f4,f5,f6] (required): "),
        "fixed_force",
    )

    run_mode(
        fixed_force=fixed_force,
        use_force_sensor=use_force_sensor,
        enabled_axes=enabled_axes,
        m_diag=m_diag,
        d_diag=d_diag,
        k_diag=k_diag,
    )

