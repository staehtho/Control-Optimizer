from app_domain.controlsys import Plant, AntiWindup
from app_domain.controlsys.PIDClosedLoop import PIDClosedLoop
from app_domain.pso_objective import compute_effective_tf_report

plant = Plant([1], [1, 0, 0])

pid_cl = PIDClosedLoop(
    plant,
    Kp=10,
    Ti=1,
    Td=1,
    Tf=0.0,
    control_constraint=[-5, 5],
    anti_windup_method=AntiWindup.CLAMPING
)

tf_report = compute_effective_tf_report(
    Td=pid_cl.Td,
    dt=1e-4,
    tf_tuning_factor_n=5.0,
    tf_limit_factor_k=5.0,
    sampling_rate_hz=None,
)
pid_cl.set_filter(Tf=tf_report.tf_effective)
