from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app_domain.controlsys import Plant
from app_domain.controlsys.freq_metrics import compute_loop_metrics_batch_from_frf


# Verification grid aligned with the MATLAB reference script.
W_MIN_EXP = -4
W_MAX_EXP = 4
W_POINTS = 4000


def make_ptn(n: int) -> Plant:
    """PTn: G(s) = 1 / (s + 1)^n with K=1 and Tm=1."""
    den = np.poly([-1.0] * int(n))
    return Plant(num=np.array([1.0], dtype=float), den=den)


def make_pt2(damping: float) -> Plant:
    """PT2: G(s) = 1 / (s^2 + 2*D*s + 1) with K=1 and Tm=1."""
    den = np.array([1.0, 2.0 * float(damping), 1.0], dtype=float)
    return Plant(num=np.array([1.0], dtype=float), den=den)


def dominant_pole_realpart_from_den(den: np.ndarray) -> float:
    """Return the dominant stable pole real part, i.e. the largest negative real part."""
    roots = np.roots(np.asarray(den, dtype=float))
    stable = roots[roots.real < 0.0]
    if stable.size == 0:
        return float(np.max(roots.real))
    return float(np.max(stable.real))


def tf_from_plant(plant: Plant) -> float:
    """Apply the project's Tf heuristic based on the dominant plant pole."""
    p_dom = dominant_pole_realpart_from_den(plant.den)
    if p_dom >= 0.0:
        return 0.01
    return (1.0 / abs(p_dom)) / 100.0


def parse_reference_cases(xlsx_path: Path) -> pd.DataFrame:
    """Parse the mixed PTn/PT2 reference workbook into a flat case table."""
    df_raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    rows = df_raw.values.tolist()

    cases: list[dict[str, float | str]] = []
    mode: str | None = None
    headers: list[str] | None = None

    for row in rows:
        if not row or all(pd.isna(value) for value in row):
            continue

        first = row[0]

        if isinstance(first, str) and first.strip() == "PTn":
            mode = "PTn"
            headers = None
            continue

        if isinstance(first, str) and first.strip() == "PT2":
            mode = "PT2"
            headers = None
            continue

        if mode in {"PTn", "PT2"} and isinstance(first, str) and first.strip() in {"n", "D"}:
            headers = [str(value).strip() if value is not None and not pd.isna(value) else "" for value in row]
            continue

        if mode in {"PTn", "PT2"} and headers is not None and isinstance(first, (int, float)) and not pd.isna(first):
            parsed = dict(zip(headers, row))
            cases.append(
                {
                    "plant_type": mode,
                    "param": float(parsed["n"]) if mode == "PTn" else float(parsed["D"]),
                    "LowerLimit": float(parsed["LowerLimit"]),
                    "UpperLimit": float(parsed["UpperLimit"]),
                    "Kp": float(parsed["Kp_PSO"]),
                    "Ti": float(parsed["Ti_PSO"]),
                    "Td": float(parsed["Td_PSO"]),
                    "ITAE_ref": float(parsed.get("ITAE_PSO_python", np.nan)),
                }
            )

    return pd.DataFrame(cases)


def load_matlab_references(script_dir: Path) -> pd.DataFrame:
    """Load and normalize the exported MATLAB reference margins if present."""
    refs: list[pd.DataFrame] = []

    pt2_path = script_dir / "Margins_PT2_Matlab.csv"
    if pt2_path.exists():
        df_pt2 = pd.read_csv(pt2_path, sep=";").rename(columns={"D": "param"})
        df_pt2["plant_type"] = "PT2"
        refs.append(df_pt2)

    ptn_path = script_dir / "Margins_PTn_Matlab.csv"
    if ptn_path.exists():
        df_ptn = pd.read_csv(ptn_path, sep=";").rename(columns={"n": "param"})
        df_ptn["plant_type"] = "PTn"
        refs.append(df_ptn)

    if not refs:
        return pd.DataFrame()

    matlab_df = pd.concat(refs, ignore_index=True, sort=False)
    matlab_df = matlab_df.rename(
        columns={
            "u_min": "LowerLimit",
            "u_max": "UpperLimit",
            "PM_deg": "pm_deg_matlab",
            "GM_dB": "gm_db_matlab",
            "Ms": "ms_matlab",
            "omega_c": "wc_matlab",
        }
    )

    keep_cols = [
        "plant_type",
        "param",
        "LowerLimit",
        "UpperLimit",
        "Tf",
        "pm_deg_matlab",
        "gm_db_matlab",
        "ms_matlab",
        "wc_matlab",
    ]
    return matlab_df[keep_cols].copy()


def evaluate_cases(df_cases: pd.DataFrame, w: np.ndarray) -> pd.DataFrame:
    """Evaluate all reference cases with the current Python implementation."""
    out: list[dict[str, float | bool | str]] = []

    for (plant_type, param), group in df_cases.groupby(["plant_type", "param"], sort=False):
        if plant_type == "PTn":
            plant = make_ptn(int(round(float(param))))
        else:
            plant = make_pt2(float(param))

        tf_used = tf_from_plant(plant)
        s = 1j * w

        with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
            G = np.asarray(plant.system(s), dtype=np.complex128)
            metrics = compute_loop_metrics_batch_from_frf(
                G=G,
                w=w,
                Kp=group["Kp"].to_numpy(dtype=float),
                Ti=group["Ti"].to_numpy(dtype=float),
                Td=group["Td"].to_numpy(dtype=float),
                Tf=np.full(group.shape[0], tf_used, dtype=float),
            )

        group = group.reset_index(drop=True)
        for idx, case in group.iterrows():
            out.append(
                {
                    "plant_type": str(plant_type),
                    "param": float(param),
                    "LowerLimit": float(case["LowerLimit"]),
                    "UpperLimit": float(case["UpperLimit"]),
                    "Kp": float(case["Kp"]),
                    "Ti": float(case["Ti"]),
                    "Td": float(case["Td"]),
                    "Tf": float(tf_used),
                    "ITAE_ref": float(case["ITAE_ref"]),
                    "numerically_valid": bool(metrics["numerically_valid_particles"][idx]),
                    "pm_deg": float(metrics["pm_deg"][idx]),
                    "gm_db": float(metrics["gm_db"][idx]),
                    "ms": float(metrics["ms"][idx]),
                    "has_wc": bool(metrics["has_wc"][idx]),
                    "has_w180": bool(metrics["has_w180"][idx]),
                    "wc": float(metrics["wc"][idx]),
                    "w180": float(metrics["w180"][idx]),
                }
            )

    return pd.DataFrame(out)


def attach_matlab_comparison(df_python: pd.DataFrame, matlab_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Python results with MATLAB references and add delta columns."""
    if matlab_df.empty:
        return df_python

    merged = df_python.merge(
        matlab_df,
        how="left",
        on=["plant_type", "param", "LowerLimit", "UpperLimit"],
    )

    merged["d_pm_deg"] = merged["pm_deg"] - merged["pm_deg_matlab"]
    merged["d_gm_db"] = merged["gm_db"] - merged["gm_db_matlab"]
    merged["d_ms"] = merged["ms"] - merged["ms_matlab"]
    merged["d_wc"] = merged["wc"] - merged["wc_matlab"]

    return merged


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    xlsx_path = script_dir / "Referenzsysteme.xlsx"

    if not xlsx_path.exists():
        raise FileNotFoundError(f"Reference workbook not found: {xlsx_path}")

    w = np.logspace(W_MIN_EXP, W_MAX_EXP, W_POINTS, dtype=np.float64)
    df_cases = parse_reference_cases(xlsx_path)
    if df_cases.empty:
        raise ValueError(f"No reference cases parsed from: {xlsx_path}")

    df_python = evaluate_cases(df_cases, w)
    df_python = df_python.sort_values(["plant_type", "param", "LowerLimit"]).reset_index(drop=True)

    matlab_df = load_matlab_references(script_dir)
    df_out = attach_matlab_comparison(df_python, matlab_df)

    out_path = script_dir / "FreqMetrics_Reference_Python.xlsx"
    df_out.to_excel(out_path, index=False)

    print(f"Loaded {len(df_cases)} reference cases from {xlsx_path.name}")
    if not matlab_df.empty:
        print("MATLAB reference CSVs loaded and merged.")
        print(
            df_out[
                [
                    "plant_type",
                    "param",
                    "LowerLimit",
                    "pm_deg",
                    "pm_deg_matlab",
                    "d_pm_deg",
                    "gm_db",
                    "gm_db_matlab",
                    "d_gm_db",
                    "ms",
                    "ms_matlab",
                    "d_ms",
                ]
            ].to_string(index=False)
        )
    else:
        print(df_out.to_string(index=False))

    print(f"\nWrote results to: {out_path}")


if __name__ == "__main__":
    main()
