import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


def select_best_gbest_marker_row(dfr: pd.DataFrame, cost_col: str):
    """Return the marker row for the run, preferring the last feasible gBest."""
    if "gbest_updated" in dfr.columns:
        gbest_rows = dfr.loc[dfr["gbest_updated"] == 1].copy()
        if not gbest_rows.empty:
            sort_cols = [col for col in ("call_id", "particle_idx") if col in gbest_rows.columns]
            if sort_cols:
                gbest_rows = gbest_rows.sort_values(sort_cols)

            if "gbest_feasible" in gbest_rows.columns:
                feasible_gbest_rows = gbest_rows.loc[gbest_rows["gbest_feasible"] == 1]
                if not feasible_gbest_rows.empty:
                    return feasible_gbest_rows.iloc[-1], "Best feasible gBest"

            return gbest_rows.iloc[-1], "Final gBest"

    return dfr.loc[dfr[cost_col].idxmin()], f"Run-Minimum ({cost_col})"


def build_best_marker_text(best_row: pd.Series, best_label: str, best_xyz: list[float], cost_col: str) -> str:
    text = (
        f"{best_label}<br>"
        f"call_id={int(best_row['call_id'])}<br>"
        f"Kp={best_xyz[0]:.3f}<br>"
        f"Ti={best_xyz[1]:.3f}<br>"
        f"Td={best_xyz[2]:.3f}"
    )

    if "gbest_feasible" in best_row.index and pd.notna(best_row["gbest_feasible"]):
        text += f"<br>gbest_feasible={int(best_row['gbest_feasible'])}"
    if "gbest_violation" in best_row.index and pd.notna(best_row["gbest_violation"]):
        text += f"<br>gbest_V={float(best_row['gbest_violation']):.6g}"
    if "gbest_perf" in best_row.index and pd.notna(best_row["gbest_perf"]):
        text += f"<br>gbest_J={float(best_row['gbest_perf']):.6g}"
    elif cost_col in best_row.index and pd.notna(best_row[cost_col]):
        text += f"<br>{cost_col}={float(best_row[cost_col]):.6g}"

    return text


def create_interactive_particle_plot(csv_path, run_id=None, out_html="particle_3d_interactive.html"):
    df = pd.read_csv(csv_path, sep=None, engine="python")
    cost_col = "total_ost" if "total_ost" in df.columns else "total_cost"

    if run_id is None:
        run_id = sorted(df["run_id"].dropna().unique())[0]

    dfr = df[df["run_id"] == run_id].copy()

    numeric_cols = [
        "Kp",
        "Ti",
        "Td",
        "V",
        cost_col,
        "call_id",
        "particle_idx",
        "gbest_updated",
        "gbest_feasible",
        "gbest_violation",
        "gbest_perf",
        "gbest_cost",
    ]
    for col in numeric_cols:
        if col in dfr.columns:
            dfr[col] = pd.to_numeric(dfr[col], errors="coerce")

    dfr = dfr.dropna(subset=["call_id", "particle_idx", "Kp", "Ti", "Td"])
    dfr["call_id"] = dfr["call_id"].astype(int)
    dfr["particle_idx"] = dfr["particle_idx"].astype(int)

    call_ids = sorted(dfr["call_id"].unique())
    best_row, best_label = select_best_gbest_marker_row(dfr, cost_col)
    best_xyz = [float(best_row["Kp"]), float(best_row["Ti"]), float(best_row["Td"])]
    best_text = build_best_marker_text(best_row, best_label, best_xyz, cost_col)

    by_call = {
        cid: dfr[dfr["call_id"] == cid].sort_values("particle_idx").copy()
        for cid in call_ids
    }

    def colors_from_v(v_series):
        values = v_series.fillna(np.nan).to_numpy(dtype=float)
        return np.where(np.isclose(values, 0.0), "green", "red")

    init_cid = call_ids[0]
    init_df = by_call[init_cid]
    init_colors = colors_from_v(init_df["V"])

    traces = [
        go.Scatter3d(
            x=init_df["Kp"],
            y=init_df["Ti"],
            z=init_df["Td"],
            mode="markers",
            marker=dict(size=5, color=init_colors, line=dict(width=1, color="black")),
            text=[
                f"particle={int(p)}<br>V={v}<br>Kp={kp:.3f}<br>Ti={ti:.3f}<br>Td={td:.3f}"
                for p, v, kp, ti, td in zip(
                    init_df["particle_idx"], init_df["V"], init_df["Kp"], init_df["Ti"], init_df["Td"]
                )
            ],
            hovertemplate="%{text}<extra></extra>",
            name="Partikel",
        ),
        go.Scatter3d(
            x=[best_xyz[0]],
            y=[best_xyz[1]],
            z=[best_xyz[2]],
            mode="markers",
            marker=dict(size=9, symbol="diamond", color="gold", line=dict(width=2, color="black")),
            text=[best_text],
            hovertemplate="%{text}<extra></extra>",
            name=best_label,
        ),
    ]

    frames = []
    for cid in call_ids:
        cur = by_call[cid]
        cur_colors = colors_from_v(cur["V"])

        frame_traces = [
            go.Scatter3d(
                x=cur["Kp"],
                y=cur["Ti"],
                z=cur["Td"],
                mode="markers",
                marker=dict(size=5, color=cur_colors, line=dict(width=1, color="black")),
                text=[
                    f"particle={int(p)}<br>V={v}<br>Kp={kp:.3f}<br>Ti={ti:.3f}<br>Td={td:.3f}"
                    for p, v, kp, ti, td in zip(
                        cur["particle_idx"], cur["V"], cur["Kp"], cur["Ti"], cur["Td"]
                    )
                ],
                hovertemplate="%{text}<extra></extra>",
                name="Partikel",
            ),
            go.Scatter3d(
                x=[best_xyz[0]],
                y=[best_xyz[1]],
                z=[best_xyz[2]],
                mode="markers",
                marker=dict(size=9, symbol="diamond", color="gold", line=dict(width=2, color="black")),
                text=[best_text],
                hovertemplate="%{text}<extra></extra>",
                name=best_label,
            ),
        ]

        frames.append(go.Frame(name=str(cid), data=frame_traces))

    fig = go.Figure(data=traces, frames=frames)
    fig.update_layout(
        title=f"Run {run_id}: Partikelbewegung im PID-Raum (interaktiv, drehbar)",
        scene=dict(
            xaxis=dict(title="Kp", range=[0, 10]),
            yaxis=dict(title="Ti", range=[0, 10]),
            zaxis=dict(title="Td", range=[0, 10]),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                x=0.02,
                y=1.02,
                direction="left",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[
                            None,
                            dict(
                                frame=dict(duration=450, redraw=True),
                                transition=dict(duration=0),
                                fromcurrent=True,
                                mode="immediate",
                            ),
                        ],
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[
                            [None],
                            dict(
                                frame=dict(duration=0, redraw=False),
                                transition=dict(duration=0),
                                mode="immediate",
                            ),
                        ],
                    ),
                ],
            )
        ],
        sliders=[
            dict(
                active=0,
                x=0.12,
                y=0.02,
                len=0.82,
                currentvalue=dict(prefix="call_id: "),
                steps=[
                    dict(
                        label=str(cid),
                        method="animate",
                        args=[
                            [str(cid)],
                            dict(
                                mode="immediate",
                                frame=dict(duration=0, redraw=True),
                                transition=dict(duration=0),
                            ),
                        ],
                    )
                    for cid in call_ids
                ],
            )
        ],
        annotations=[
            dict(
                text=f"Farben: gruen = V=0, rot = V!=0 | Goldener Marker = {best_label}",
                x=0.01,
                y=0.96,
                xref="paper",
                yref="paper",
                showarrow=False,
                align="left",
            )
        ],
    )

    pio.write_html(fig, file=str(out_html), auto_open=False, include_plotlyjs="cdn", full_html=True)
    return str(out_html)


if __name__ == "__main__":
    out = create_interactive_particle_plot("particle_log.csv", run_id=0, out_html="particle_run0_3d_interactive.html")
    print("Gespeichert:", out)
