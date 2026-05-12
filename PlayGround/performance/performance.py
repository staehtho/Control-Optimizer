import json
import numpy as np
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from tqdm import tqdm

from app_domain.controlsys import Plant
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.pso_objective import PsoFunc
from app_domain.pso_objective import pso_func as pso_module
from app_domain.PSO import Swarm


class TimingStats:
    def __init__(self) -> None:
        self.totals: dict[str, float] = {}
        self.counts: dict[str, int] = {}

    @contextmanager
    def measure(self, label: str):
        start = perf_counter()
        try:
            yield
        finally:
            self.totals[label] = self.totals.get(label, 0.0) + (perf_counter() - start)
            self.counts[label] = self.counts.get(label, 0) + 1

    def wrap(self, label: str, func):
        def wrapped(*args, **kwargs):
            with self.measure(label):
                return func(*args, **kwargs)

        return wrapped

    def print_summary(self) -> None:
        print("\nTiming summary")
        print("-" * 85)
        for label in sorted(self.totals):
            total = self.totals[label]
            count = self.counts[label]
            avg = total / count if count else 0.0
            print(f"{label:30s} total={total:10.6f}s  count={count:6d}  avg={avg:10.6f}s")

    def to_dict(self) -> dict[str, dict[str, float | int]]:
        summary: dict[str, dict[str, float | int]] = {}
        for label in sorted(self.totals):
            total = self.totals[label]
            count = self.counts[label]
            summary[label] = {
                "total_seconds": total,
                "count": count,
                "avg_seconds": total / count if count else 0.0,
            }
        return summary


@contextmanager
def patch_timing(objective: PsoFunc, stats: TimingStats):
    originals = {
        "compute_effective_tf_batch": pso_module.compute_effective_tf_batch,
        "compute_loop_metrics_batch": pso_module.compute_loop_metrics_batch,
        "time_domain_pso_func": pso_module.time_domain_pso_func,
        "evaluate_candidates": objective.evaluate_candidates,
    }

    pso_module.compute_effective_tf_batch = stats.wrap(
        "compute_effective_tf_batch", pso_module.compute_effective_tf_batch
    )
    pso_module.compute_loop_metrics_batch = stats.wrap(
        "compute_loop_metrics_batch", pso_module.compute_loop_metrics_batch
    )
    pso_module.time_domain_pso_func = stats.wrap(
        "time_domain_pso_func", pso_module.time_domain_pso_func
    )
    objective.evaluate_candidates = stats.wrap("evaluate_candidates", objective.evaluate_candidates)

    try:
        yield
    finally:
        pso_module.compute_effective_tf_batch = originals["compute_effective_tf_batch"]
        pso_module.compute_loop_metrics_batch = originals["compute_loop_metrics_batch"]
        pso_module.time_domain_pso_func = originals["time_domain_pso_func"]
        objective.evaluate_candidates = originals["evaluate_candidates"]


def main():

    src = Path(__file__).parent

    configs: list[Path] = []
    for item in src.iterdir():
        if item.is_dir():
            for file in item.iterdir():
                if file.stem == "config":
                    configs.append(file)

    for file in configs:

        with open(str(file), "r", encoding="utf-8") as f:
            config = json.load(f)

        stats = TimingStats()
        output_path = file.parent / "results.json"

        plant = Plant([1], [1, 3, 3, 1])
        pid = PIDClosedLoop(plant)

        objective = PsoFunc(
            controller=pid,
            t0=config["t0"],
            t1=config["t1"],
            dt=config["dt"],
            r=lambda t: np.ones_like(t),
            sampling_rate_hz=config["sampling_rate_hz"],
            use_overshoot_control=config["use_overshoot_control"],
            allowed_overshoot_pct=config["allowed_overshoot_pct"],
            use_max_du_dt_constraint=config["use_max_du_dt_constraint"],
            allowed_max_du_dt=config["allowed_max_du_dt"],
            du_dt_window_steps=config["du_dt_window_steps"],
            use_freq_metrics=config["use_freq_metrics"],
            gm_min_db=config["gm_min_db"],
            pm_min_deg=config["gm_min_db"],
            ms_max_db=config["ms_max_db"] if config["ms_max_db"] != "" else None,
            pre_compiling=False,
        )

        swarm = Swarm(objective, 40, 3, [[0, 0, 0], [10, 10, 10]])
        swarm.simulate_swarm()

        with patch_timing(objective, stats):
            for _ in tqdm(range(100), desc=f"{file.parent.stem}"):
                swarm = Swarm(objective, 40, 3, [[0, 0, 0], [10, 10, 10]])
                swarm.simulate_swarm = stats.wrap("simulate_swarm", swarm.simulate_swarm)
                swarm.simulate_swarm()

        stats.print_summary()
        output_path.write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")
        print(f"\nSaved JSON results to {output_path}")


if __name__ == "__main__":
    main()
