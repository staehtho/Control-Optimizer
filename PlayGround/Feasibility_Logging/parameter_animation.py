import pandas as pd
import numpy as np
from pathlib import Path


# Try to import plotly; if missing, write a helpful script anyway
try:
    import plotly.graph_objects as go
    import plotly.io as pio
    plotly_available = True
except Exception as e:
    plotly_available = False
    plotly_import_error = str(e)

base_dir = Path(__file__).resolve().parent

csv_path = base_dir / "particle_log.csv"   # Dateiname anpassen falls anders
html_path = base_dir / "particle_run0_3d_interactive.html"
py_path = base_dir / "particle_3d_plotly_interactive.py"

df = pd.read_csv(csv_path, sep=";")
cost_col = "total_ost" if "total_ost" in df.columns else "total_cost"

run_id = sorted(df["run_id"].dropna().unique())[0]
dfr = df[df["run_id"] == run_id].copy()

for c in ["Kp", "Ti", "Td", "V", cost_col, "call_id", "particle_idx"]:
    if c in dfr.columns:
        dfr[c] = pd.to_numeric(dfr[c], errors="coerce")

dfr = dfr.dropna(subset=["call_id", "particle_idx", "Kp", "Ti", "Td"])
dfr["call_id"] = dfr["call_id"].astype(int)
dfr["particle_idx"] = dfr["particle_idx"].astype(int)

call_ids = sorted(dfr["call_id"].unique())
particle_ids = sorted(dfr["particle_idx"].unique())

best_row = dfr.loc[dfr[cost_col].idxmin()]
best_xyz = [float(best_row["Kp"]), float(best_row["Ti"]), float(best_row["Td"])]

# Precompute per-particle paths
by_particle = {pid: dfr[dfr["particle_idx"] == pid].sort_values("call_id").copy() for pid in particle_ids}
by_call = {cid: dfr[dfr["call_id"] == cid].sort_values("particle_idx").copy() for cid in call_ids}

def colors_from_v(v_series):
    return np.where(np.isclose(v_series.fillna(np.nan).to_numpy(dtype=float), 0.0), "green", "red")

if plotly_available:
    # Initial frame data
    init_cid = call_ids[0]
    init_df = by_call[init_cid]
    init_colors = colors_from_v(init_df["V"])

    # Base traces: trails (one per particle), current positions, best point
    traces = []

    # 0..N-1 trails
    for pid in particle_ids:
        g = by_particle[pid]
        g2 = g[g["call_id"] <= init_cid]
        traces.append(
            go.Scatter3d(
                x=g2["Kp"], y=g2["Ti"], z=g2["Td"],
                mode="lines",
                line=dict(width=3),
                opacity=0.35,
                showlegend=False,
                hoverinfo="skip",
                name=f"Trail p{pid}"
            )
        )

    # Current particle positions
    traces.append(
        go.Scatter3d(
            x=init_df["Kp"], y=init_df["Ti"], z=init_df["Td"],
            mode="markers",
            marker=dict(size=5, color=init_colors, line=dict(width=1, color="black")),
            text=[f"particle={int(p)}<br>V={v}<br>Kp={kp:.3f}<br>Ti={ti:.3f}<br>Td={td:.3f}"
                  for p, v, kp, ti, td in zip(init_df["particle_idx"], init_df["V"], init_df["Kp"], init_df["Ti"], init_df["Td"])],
            hovertemplate="%{text}<extra></extra>",
            name="Partikel"
        )
    )

    # Global best point (always visible)
    traces.append(
        go.Scatter3d(
            x=[best_xyz[0]], y=[best_xyz[1]], z=[best_xyz[2]],
            mode="markers",
            marker=dict(size=9, symbol="diamond", color="gold", line=dict(width=2, color="black")),
            text=[f"Globales Minimum ({cost_col})<br>{cost_col}={best_row[cost_col]:.6g}<br>Kp={best_xyz[0]:.3f}<br>Ti={best_xyz[1]:.3f}<br>Td={best_xyz[2]:.3f}"],
            hovertemplate="%{text}<extra></extra>",
            name="Globales Minimum"
        )
    )

    frames = []
    for cid in call_ids:
        cur = by_call[cid]
        cur_colors = colors_from_v(cur["V"])

        frame_traces = []
        # trails update for each particle
        for pid in particle_ids:
            g = by_particle[pid]
            g2 = g[g["call_id"] <= cid]
            frame_traces.append(
                go.Scatter3d(
                    x=g2["Kp"], y=g2["Ti"], z=g2["Td"],
                    mode="lines",
                    line=dict(width=3),
                    opacity=0.35,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # current points
        frame_traces.append(
            go.Scatter3d(
                x=cur["Kp"], y=cur["Ti"], z=cur["Td"],
                mode="markers",
                marker=dict(size=5, color=cur_colors, line=dict(width=1, color="black")),
                text=[f"particle={int(p)}<br>V={v}<br>Kp={kp:.3f}<br>Ti={ti:.3f}<br>Td={td:.3f}"
                      for p, v, kp, ti, td in zip(cur["particle_idx"], cur["V"], cur["Kp"], cur["Ti"], cur["Td"])],
                hovertemplate="%{text}<extra></extra>",
                name="Partikel"
            )
        )

        # best point unchanged
        frame_traces.append(
            go.Scatter3d(
                x=[best_xyz[0]], y=[best_xyz[1]], z=[best_xyz[2]],
                mode="markers",
                marker=dict(size=9, symbol="diamond", color="gold", line=dict(width=2, color="black")),
                text=[f"Globales Minimum ({cost_col})<br>{cost_col}={best_row[cost_col]:.6g}<br>Kp={best_xyz[0]:.3f}<br>Ti={best_xyz[1]:.3f}<br>Td={best_xyz[2]:.3f}"],
                hovertemplate="%{text}<extra></extra>",
                name="Globales Minimum"
            )
        )

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
        legend=dict(itemsizing="constant"),
        margin=dict(l=0, r=0, t=60, b=0),
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            x=0.02, y=1.02,
            direction="left",
            buttons=[
                dict(
                    label="▶ Play",
                    method="animate",
                    args=[None, dict(frame=dict(duration=450, redraw=True),
                                     transition=dict(duration=0),
                                     fromcurrent=True,
                                     mode="immediate")]
                ),
                dict(
                    label="⏸ Pause",
                    method="animate",
                    args=[[None], dict(frame=dict(duration=0, redraw=False),
                                       transition=dict(duration=0),
                                       mode="immediate")]
                )
            ]
        )],
        sliders=[dict(
            active=0,
            x=0.12, y=0.02, len=0.82,
            currentvalue=dict(prefix="call_id: "),
            steps=[
                dict(
                    label=str(cid),
                    method="animate",
                    args=[[str(cid)], dict(mode="immediate",
                                           frame=dict(duration=0, redraw=True),
                                           transition=dict(duration=0))]
                ) for cid in call_ids
            ]
        )],
        annotations=[
            dict(
                text="Farben: grün = V=0, rot = V≠0 | Goldener Marker = globales Minimum",
                x=0.01, y=0.96, xref="paper", yref="paper", showarrow=False, align="left"
            )
        ]
    )

    pio.write_html(fig, file=str(html_path), auto_open=False, include_plotlyjs="cdn", full_html=True)

# Save reusable script (works on user's machine)
script_text = r'''
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio

def create_interactive_particle_plot(csv_path, run_id=None, out_html="particle_3d_interactive.html"):
    df = pd.read_csv(csv_path, sep=";")
    cost_col = "total_ost" if "total_ost" in df.columns else "total_cost"

    if run_id is None:
        run_id = sorted(df["run_id"].dropna().unique())[0]

    dfr = df[df["run_id"] == run_id].copy()

    for c in ["Kp", "Ti", "Td", "V", cost_col, "call_id", "particle_idx"]:
        if c in dfr.columns:
            dfr[c] = pd.to_numeric(dfr[c], errors="coerce")

    dfr = dfr.dropna(subset=["call_id", "particle_idx", "Kp", "Ti", "Td"])
    dfr["call_id"] = dfr["call_id"].astype(int)
    dfr["particle_idx"] = dfr["particle_idx"].astype(int)

    call_ids = sorted(dfr["call_id"].unique())
    particle_ids = sorted(dfr["particle_idx"].unique())

    best_row = dfr.loc[dfr[cost_col].idxmin()]
    best_xyz = [float(best_row["Kp"]), float(best_row["Ti"]), float(best_row["Td"])]

    by_particle = {pid: dfr[dfr["particle_idx"] == pid].sort_values("call_id").copy() for pid in particle_ids}
    by_call = {cid: dfr[dfr["call_id"] == cid].sort_values("particle_idx").copy() for cid in call_ids}

    def colors_from_v(v_series):
        return np.where(np.isclose(v_series.fillna(np.nan).to_numpy(dtype=float), 0.0), "green", "red")

    init_cid = call_ids[0]
    init_df = by_call[init_cid]
    init_colors = colors_from_v(init_df["V"])

    traces = []
    for pid in particle_ids:
        g2 = by_particle[pid][by_particle[pid]["call_id"] <= init_cid]
        traces.append(go.Scatter3d(
            x=g2["Kp"], y=g2["Ti"], z=g2["Td"],
            mode="lines", line=dict(width=3), opacity=0.35,
            showlegend=False, hoverinfo="skip"
        ))

    traces.append(go.Scatter3d(
        x=init_df["Kp"], y=init_df["Ti"], z=init_df["Td"],
        mode="markers",
        marker=dict(size=5, color=init_colors, line=dict(width=1, color="black")),
        text=[f"particle={int(p)}<br>V={v}<br>Kp={kp:.3f}<br>Ti={ti:.3f}<br>Td={td:.3f}"
              for p, v, kp, ti, td in zip(init_df["particle_idx"], init_df["V"], init_df["Kp"], init_df["Ti"], init_df["Td"])],
        hovertemplate="%{text}<extra></extra>",
        name="Partikel"
    ))

    traces.append(go.Scatter3d(
        x=[best_xyz[0]], y=[best_xyz[1]], z=[best_xyz[2]],
        mode="markers",
        marker=dict(size=9, symbol="diamond", color="gold", line=dict(width=2, color="black")),
        text=[f"Globales Minimum ({cost_col})<br>{cost_col}={best_row[cost_col]:.6g}<br>Kp={best_xyz[0]:.3f}<br>Ti={best_xyz[1]:.3f}<br>Td={best_xyz[2]:.3f}"],
        hovertemplate="%{text}<extra></extra>",
        name="Globales Minimum"
    ))

    frames = []
    for cid in call_ids:
        cur = by_call[cid]
        cur_colors = colors_from_v(cur["V"])

        frame_traces = []
        for pid in particle_ids:
            g2 = by_particle[pid][by_particle[pid]["call_id"] <= cid]
            frame_traces.append(go.Scatter3d(
                x=g2["Kp"], y=g2["Ti"], z=g2["Td"],
                mode="lines", line=dict(width=3), opacity=0.35,
                showlegend=False, hoverinfo="skip"
            ))

        frame_traces.append(go.Scatter3d(
            x=cur["Kp"], y=cur["Ti"], z=cur["Td"],
            mode="markers",
            marker=dict(size=5, color=cur_colors, line=dict(width=1, color="black")),
            text=[f"particle={int(p)}<br>V={v}<br>Kp={kp:.3f}<br>Ti={ti:.3f}<br>Td={td:.3f}"
                  for p, v, kp, ti, td in zip(cur["particle_idx"], cur["V"], cur["Kp"], cur["Ti"], cur["Td"])],
            hovertemplate="%{text}<extra></extra>",
            name="Partikel"
        ))

        frame_traces.append(go.Scatter3d(
            x=[best_xyz[0]], y=[best_xyz[1]], z=[best_xyz[2]],
            mode="markers",
            marker=dict(size=9, symbol="diamond", color="gold", line=dict(width=2, color="black")),
            text=[f"Globales Minimum ({cost_col})<br>{cost_col}={best_row[cost_col]:.6g}<br>Kp={best_xyz[0]:.3f}<br>Ti={best_xyz[1]:.3f}<br>Td={best_xyz[2]:.3f}"],
            hovertemplate="%{text}<extra></extra>",
            name="Globales Minimum"
        ))

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
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            x=0.02, y=1.02,
            direction="left",
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=450, redraw=True),
                                      transition=dict(duration=0),
                                      fromcurrent=True, mode="immediate")]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        transition=dict(duration=0), mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0, x=0.12, y=0.02, len=0.82,
            currentvalue=dict(prefix="call_id: "),
            steps=[dict(label=str(cid), method="animate",
                        args=[[str(cid)], dict(mode="immediate",
                                               frame=dict(duration=0, redraw=True),
                                               transition=dict(duration=0))])
                   for cid in call_ids]
        )],
        annotations=[dict(
            text="Farben: grün = V=0, rot = V≠0 | Goldener Marker = globales Minimum",
            x=0.01, y=0.96, xref="paper", yref="paper", showarrow=False, align="left"
        )]
    )

    pio.write_html(fig, file=str(out_html), auto_open=False, include_plotlyjs="cdn", full_html=True)
    return str(out_html)

if __name__ == "__main__":
    out = create_interactive_particle_plot("particle_log.csv", run_id=0, out_html="particle_run0_3d_interactive.html")
    print("Gespeichert:", out)
'''
py_path.write_text(script_text, encoding="utf-8")

if plotly_available:
    print(f"Interaktive HTML erstellt: {html_path}")
else:
    print("Plotly konnte hier nicht importiert werden.")
    print(f"Fehler: {plotly_import_error}")

print(f"Skript erstellt: {py_path}")
print(f"run_id={run_id}, Calls={len(call_ids)}, Partikel={len(particle_ids)}")
