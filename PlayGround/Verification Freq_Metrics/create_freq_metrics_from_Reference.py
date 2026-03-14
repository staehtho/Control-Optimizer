from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Import-Pfad so wie bei dir im Playground üblich
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from app_domain.controlsys import Plant
from app_domain.controlsys.freq_metrics import compute_loop_metrics_batch

# ─────────────────────────────────────────────────────────────────────────────
# Plant-Konstruktion (K=1, Tm=1)

def make_ptn(n: int) -> Plant:
    """PTn: G(s) = 1 / (s+1)^n  (K=1, Tm=1)."""
    den = np.poly([-1.0] * int(n))  # (s+1)^n
    num = np.array([1.0], dtype=float)
    return Plant(num=num, den=den)

def make_pt2(D: float) -> Plant:
    """PT2: G(s) = 1 / (s^2 + 2*D*s + 1)  (K=1, Tm=1)."""
    D = float(D)
    den = np.array([1.0, 2.0 * D, 1.0], dtype=float)
    num = np.array([1.0], dtype=float)
    return Plant(num=num, den=den)

# ─────────────────────────────────────────────────────────────────────────────
# Tf-Heuristik (wie du sie beschrieben hast)

def dominant_pole_realpart_from_den(den: np.ndarray) -> float:
    """
    Dominanter Pol = am nächsten an der jω-Achse (von links),
    also max(real part) unter den stabilen Polen.
    """
    roots = np.roots(np.asarray(den, dtype=float))
    stable = roots[roots.real < 0]
    if stable.size == 0:
        # keine stabilen Pole -> z.B. marginal/instabil
        return float(np.max(roots.real))
    return float(np.max(stable.real))

def tf_from_plant(plant: Plant) -> float:
    """
    Deine Policy:
      - wenn p_dom >= 0 => Tf = 0.01
      - sonst Tf = (1/|p_dom|)/100
    """
    p_dom = dominant_pole_realpart_from_den(plant.den)
    if p_dom >= 0:
        return 0.01
    t_dom = 1.0 / abs(p_dom)
    return t_dom / 100.0

# ─────────────────────────────────────────────────────────────────────────────
# Excel-Parsing: Layout wie in Referenzsysteme.xlsx

def parse_reference_cases(xlsx_path: Path) -> pd.DataFrame:
    df_raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    rows = df_raw.values.tolist()

    cases = []
    mode = None
    headers = None

    for r in rows:
        if not r or all(pd.isna(x) for x in r):
            continue

        first = r[0]

        if isinstance(first, str) and first.strip() == "PTn":
            mode = "PTn"
            headers = None
            continue

        if isinstance(first, str) and first.strip() == "PT2":
            mode = "PT2"
            headers = None
            continue

        # Headerzeile innerhalb eines Blocks
        if mode in ("PTn", "PT2") and isinstance(first, str) and first.strip() in ("n", "D"):
            headers = [str(x).strip() if x is not None and not pd.isna(x) else "" for x in r]
            continue

        # Datenzeile: beginnt mit Zahl (n oder D)
        if mode in ("PTn", "PT2") and headers is not None and isinstance(first, (int, float)) and not pd.isna(first):
            row = dict(zip(headers, r))

            cases.append({
                "plant_type": mode,
                "param": float(row["n"]) if mode == "PTn" else float(row["D"]),  # n oder D
                "LowerLimit": float(row["LowerLimit"]),
                "UpperLimit": float(row["UpperLimit"]),
                "Kp": float(row["Kp_PSO"]),
                "Ti": float(row["Ti_PSO"]),
                "Td": float(row["Td_PSO"]),
                "ITAE_ref": float(row.get("ITAE_PSO_python", np.nan)),
            })

    return pd.DataFrame(cases)

# ─────────────────────────────────────────────────────────────────────────────
# Evaluation

def evaluate_cases(df_cases: pd.DataFrame, adaptive_range: bool = True) -> pd.DataFrame:
    out = []

    for _, c in df_cases.iterrows():
        plant_type = c["plant_type"]
        n_or_D = c["param"]

        if plant_type == "PTn":
            plant = make_ptn(int(round(n_or_D)))
        else:
            plant = make_pt2(float(n_or_D))

        Tf = tf_from_plant(plant)

        # Batch-Call (P=1)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
            metrics = compute_loop_metrics_batch(
                plant=plant,
                Kp=np.array([c["Kp"]], dtype=float),
                Ti=np.array([c["Ti"]], dtype=float),
                Td=np.array([c["Td"]], dtype=float),
                Tf=np.array([Tf], dtype=float),
                adaptive_range=adaptive_range,
            )

        out.append({
            "plant_type": plant_type,
            "n_or_D": n_or_D,
            "LowerLimit": c["LowerLimit"],
            "UpperLimit": c["UpperLimit"],
            "Kp": c["Kp"],
            "Ti": c["Ti"],
            "Td": c["Td"],
            "Tf": Tf,
            "ITAE_ref": c["ITAE_ref"],

            "ok": bool(metrics.get("ok_particles", np.array([True]))[0]),
            "pm_deg": float(metrics["pm_deg"][0]),
            "gm_db": float(metrics["gm_db"][0]),
            "ms": float(metrics["ms"][0]),
            "has_wc": bool(metrics["has_wc"][0]),
            "has_w180": bool(metrics["has_w180"][0]),
            "wc": float(metrics["wc"][0]),
            "w180": float(metrics["w180"][0]),
        })

    return pd.DataFrame(out)

# ─────────────────────────────────────────────────────────────────────────────
# Main

def main():
    script_dir = Path(__file__).resolve().parent

    print("SCRIPT:", Path(__file__).resolve())
    print("CWD   :", Path.cwd().resolve())

    xlsx_path = script_dir / "Referenzsysteme.xlsx"
    print("EXCEL :", xlsx_path)
    print("EXISTS:", xlsx_path.exists())

    df_cases = parse_reference_cases(xlsx_path)
    print(f"Loaded {len(df_cases)} cases from {xlsx_path.name}")

    df_out = evaluate_cases(df_cases, adaptive_range=True)
    df_out = df_out.sort_values(["plant_type", "n_or_D", "LowerLimit"]).reset_index(drop=True)

    print(df_out)

    out_path = script_dir / "FreqMetrics_Reference_Python.xlsx"
    df_out.to_excel(out_path, index=False)
    print(f"\nWrote results to: {out_path}")

if __name__ == "__main__":
    main()