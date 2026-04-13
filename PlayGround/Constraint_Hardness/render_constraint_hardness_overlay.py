from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pt2_constraint_hardness_scan as scan


DEFAULT_RESULTS_DIR = SCRIPT_DIR / "results" / "oscillatory_d01_u100"
DEFAULT_PLOT_READY_CSV = DEFAULT_RESULTS_DIR / "pt2_constraint_hardness_plot_ready.csv"
DEFAULT_STACKED_CSV = DEFAULT_RESULTS_DIR / "pt2_constraint_hardness_stacked_label_ready.csv"
DEFAULT_PNG = DEFAULT_RESULTS_DIR / "constraint_hardness_overlay_stacked_labels.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the stacked-label constraint-hardness overlay from an existing plot-ready CSV."
    )
    parser.add_argument(
        "--plot-ready-csv",
        type=Path,
        default=DEFAULT_PLOT_READY_CSV,
        help="Input CSV produced by pt2_constraint_hardness_scan.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory for the generated stacked-label CSV and PNG",
    )
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    plot_ready_csv = args.plot_ready_csv.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_rows = read_csv_rows(plot_ready_csv)
    stacked_rows = scan.build_stacked_label_ready_rows(plot_rows)

    stacked_csv_path = output_dir / DEFAULT_STACKED_CSV.name
    png_path = output_dir / DEFAULT_PNG.name

    scan.write_csv(stacked_csv_path, stacked_rows)
    scan.try_create_stacked_label_overlay_plot(stacked_rows, output_dir)

    print(f"Wrote stacked-label CSV to: {stacked_csv_path}")
    print(f"Wrote overlay PNG to:      {png_path}")


if __name__ == "__main__":
    main()
