from pathlib import Path

import pandas as pd


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "particle_log.csv"
    xlsx_path = base_dir / "particle_log.xlsx"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing log file: {csv_path}")

    # Works for old ';' logs and new ',' logs.
    df = pd.read_csv(csv_path, sep=None, engine="python")

    # Ensure current metric columns exist even for legacy logs.
    for col in (
        "overshoot_pct",
        "max_du_dt",
        "time_cost",
        "total_cost",
        "V",
        "V_du",
        "time_simulated",
    ):
        if col not in df.columns:
            df[col] = pd.NA

    summary = (
        df.groupby("run_id", dropna=False)
        .agg(
            calls=("call_id", "nunique"),
            particles=("particle_idx", "nunique"),
            best_total_cost=("total_cost", "min"),
            best_violation=("V", "min"),
            min_overshoot_pct=("overshoot_pct", "min"),
            max_overshoot_pct=("overshoot_pct", "max"),
            min_max_du_dt=("max_du_dt", "min"),
            max_max_du_dt=("max_du_dt", "max"),
        )
        .reset_index()
    )

    with pd.ExcelWriter(xlsx_path) as writer:
        df.to_excel(writer, sheet_name="particle_log", index=False)
        summary.to_excel(writer, sheet_name="run_summary", index=False)

    print(f"Wrote: {xlsx_path}")


if __name__ == "__main__":
    main()
