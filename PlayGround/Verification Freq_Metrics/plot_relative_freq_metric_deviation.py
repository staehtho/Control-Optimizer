from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter, NullLocator


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = SCRIPT_DIR / "FreqMetrics_Reference_Python.xlsx"
DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[3]
    / "BA-Dokumentation"
    / "Figures"
)

LIMIT_ORDER = [-2.0, -3.0, -5.0, -10.0]
LIMIT_LABELS = {
    -2.0: "±2",
    -3.0: "±3",
    -5.0: "±5",
    -10.0: "±10",
}
LIMIT_COLORS = {
    -2.0: "#ff7f0e",
    -3.0: "#2ca02c",
    -5.0: "#d62728",
    -10.0: "#1f77b4",
}

METRIC_SPECS = (
    ("pm_rel_pct", r"Phasenreserve $\varphi_m$"),
    ("gm_rel_pct", r"Amplitudenreserve $\mathit{gm}$"),
    ("smax_rel_pct", r"Sensitivitätsmaximum $\mathit{S}_{max}$"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot relative deviations of Python frequency metrics against MATLAB references."
    )
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def relative_deviation_percent(py_value: float, matlab_value: float) -> float:
    if np.isinf(py_value) and np.isinf(matlab_value) and np.sign(py_value) == np.sign(matlab_value):
        return 0.0
    if np.isinf(py_value) or np.isinf(matlab_value):
        return np.inf
    if np.isnan(py_value) or np.isnan(matlab_value):
        return np.nan

    denom = abs(matlab_value)
    if np.isclose(denom, 0.0):
        return 0.0 if np.isclose(py_value, 0.0) else np.inf

    return abs(py_value - matlab_value) / denom * 100.0


def load_metrics(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    df["smax_py"] = 10.0 ** (df["ms_db"].to_numpy(dtype=float) / 20.0)
    df["smax_matlab"] = 10.0 ** (df["ms_db_matlab"].to_numpy(dtype=float) / 20.0)

    df["pm_rel_pct"] = [
        relative_deviation_percent(py_value, matlab_value)
        for py_value, matlab_value in zip(
            df["pm_deg"].to_numpy(dtype=float),
            df["pm_deg_matlab"].to_numpy(dtype=float),
        )
    ]
    df["gm_rel_pct"] = [
        relative_deviation_percent(py_value, matlab_value)
        for py_value, matlab_value in zip(
            df["gm_db"].to_numpy(dtype=float),
            df["gm_db_matlab"].to_numpy(dtype=float),
        )
    ]
    df["gm_both_inf"] = (
        np.isinf(df["gm_db"].to_numpy(dtype=float))
        & np.isinf(df["gm_db_matlab"].to_numpy(dtype=float))
    )
    df["smax_rel_pct"] = [
        relative_deviation_percent(py_value, matlab_value)
        for py_value, matlab_value in zip(
            df["smax_py"].to_numpy(dtype=float),
            df["smax_matlab"].to_numpy(dtype=float),
        )
    ]

    return df


def format_param_label(plant_type: str, param: float) -> str:
    if plant_type == "PTn":
        return f"n={int(round(param))}"
    return f"D={param:.1f}"


def compute_axis_scale(values: np.ndarray) -> tuple[float, float, float]:
    finite_positive = values[np.isfinite(values) & (values > 0.0)]

    if finite_positive.size == 0:
        floor_value = 1e-12
        top_finite = 1.0
    else:
        min_positive = float(np.min(finite_positive))
        max_positive = float(np.max(finite_positive))
        floor_value = max(10.0 ** np.floor(np.log10(min_positive)) / 10.0, 1e-12)
        top_finite = max_positive

    inf_cap = top_finite * 20.0
    y_top = inf_cap * 4.0 if np.isinf(values).any() else top_finite * 8.0
    y_top = max(y_top, floor_value * 100.0)

    return floor_value, inf_cap, y_top


def prepare_metric_value(row: pd.Series, metric_column: str) -> float:
    value = float(row[metric_column])

    if metric_column == "gm_rel_pct" and bool(row.get("gm_both_inf", False)):
        return np.nan

    return value


def plot_family(df: pd.DataFrame, plant_type: str, output_basename: Path) -> None:
    family_df = df[df["plant_type"] == plant_type].copy()
    unique_params = sorted(family_df["param"].unique())
    x = np.arange(len(unique_params), dtype=float)
    width = 0.18
    metric_specs = [
        metric_spec
        for metric_spec in METRIC_SPECS
        if not (plant_type == "PT2" and metric_spec[0] == "gm_rel_pct")
    ]

    fig_height = 8.8 if len(metric_specs) == 3 else 6.4
    fig, axes = plt.subplots(len(metric_specs), 1, figsize=(10.2, fig_height), sharex=True)
    if len(metric_specs) == 1:
        axes = [axes]

    for ax, (metric_column, metric_label) in zip(axes, metric_specs):
        raw_matrix = np.full((len(LIMIT_ORDER), len(unique_params)), np.nan, dtype=float)
        for limit_index, lower_limit in enumerate(LIMIT_ORDER):
            for param_index, param in enumerate(unique_params):
                row = family_df[
                    (np.isclose(family_df["param"], param))
                    & (np.isclose(family_df["LowerLimit"], lower_limit))
                ]
                if row.empty:
                    continue
                raw_matrix[limit_index, param_index] = prepare_metric_value(
                    row.iloc[0],
                    metric_column,
                )

        floor_value, inf_cap, y_top = compute_axis_scale(raw_matrix.reshape(-1))

        for limit_index, lower_limit in enumerate(LIMIT_ORDER):
            raw_values = raw_matrix[limit_index]
            finite_mask = np.isfinite(raw_values)
            if metric_column == "gm_rel_pct":
                finite_mask &= ~np.isinf(raw_values)
            if not np.any(finite_mask):
                continue

            plot_values = np.array(raw_values, copy=True)
            plot_values[np.isnan(plot_values)] = np.nan
            plot_values[np.isinf(plot_values)] = np.nan
            zero_mask = np.isfinite(plot_values) & (plot_values == 0.0)
            plot_values[zero_mask] = floor_value

            bars = ax.bar(
                x + (limit_index - 1.5) * width,
                plot_values,
                width=width,
                color=LIMIT_COLORS[lower_limit],
                label=LIMIT_LABELS[lower_limit],
            )

        ax.set_yscale("log")
        ax.set_ylim(floor_value / 2.0, y_top)
        ax.set_ylabel("Relative\nAbweichung [%]", fontsize=12)
        ax.set_title(metric_label, fontsize=14)
        ax.grid(True, axis="y", alpha=0.3)
        ax.tick_params(axis="y", which="major", labelsize=10, labelleft=True)
        ax.yaxis.set_major_locator(LogLocator(base=10.0))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_formatter(LogFormatterMathtext())

    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(
        [format_param_label(plant_type, float(param)) for param in unique_params],
        fontsize=11,
    )
    axes[-1].tick_params(axis="x", labelsize=11)

    legend_handles = [
        plt.Rectangle((0.0, 0.0), 1.0, 1.0, color=LIMIT_COLORS[limit])
        for limit in LIMIT_ORDER
    ]
    fig.legend(
        legend_handles,
        [LIMIT_LABELS[limit] for limit in LIMIT_ORDER],
        title="Stellgrössenbegrenzung",
        loc="upper right",
        frameon=True,
        fontsize=10,
        title_fontsize=10,
    )

    fig.tight_layout(rect=(0.0, 0.0, 0.93, 0.98))
    fig.savefig(output_basename.with_suffix(".pdf"))
    fig.savefig(output_basename.with_suffix(".png"), dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    metrics_df = load_metrics(args.data_path.resolve())

    plot_family(
        metrics_df,
        plant_type="PTn",
        output_basename=args.output_dir.resolve() / "freq_metrics_relative_deviation_ptn",
    )
    plot_family(
        metrics_df,
        plant_type="PT2",
        output_basename=args.output_dir.resolve() / "freq_metrics_relative_deviation_pt2",
    )

    print(f"Wrote {(args.output_dir / 'freq_metrics_relative_deviation_ptn.pdf').resolve()}")
    print(f"Wrote {(args.output_dir / 'freq_metrics_relative_deviation_ptn.png').resolve()}")
    print(f"Wrote {(args.output_dir / 'freq_metrics_relative_deviation_pt2.pdf').resolve()}")
    print(f"Wrote {(args.output_dir / 'freq_metrics_relative_deviation_pt2.png').resolve()}")


if __name__ == "__main__":
    main()
