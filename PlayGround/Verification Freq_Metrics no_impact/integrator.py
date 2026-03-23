from app_domain.controlsys import Plant, PIDClosedLoop, dominant_pole_realpart, AntiWindup

plant = Plant([1], [1, 0, 0])

pid_cl = PIDClosedLoop(
    plant,
    Kp=10,
    Ti=1,
    Td=1,
    control_constraint=[-5, 5],
    anti_windup_method=AntiWindup.CLAMPING
)

# Determine dominant pole
p_dom = dominant_pole_realpart(plant.den)

if p_dom >= 0:
    tf = 0.01
else:
    t_dom = 1 / abs(p_dom)
    tf = t_dom / 100

pid_cl.set_filter(Tf=tf)
