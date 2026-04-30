clear
clc
close all

s = tf('s');

		
% neu
Kp = 9.682516169;	
Ti = 3.310660834;
Td = 0.464654242;
Tf = 0.092930848;
		

% alt
Kp = 9.973304515;	
Ti = 4.545077959;
Td = 0.483106422;
Tf = 0.01;


filter = s / ( Tf * s + 1); 

constraint = 10;
plant = tf(1, [1 0 1]);

default_start_time = 0.0;
default_end_time = 20.0;
default_time_step = 1e-4;

model_file = "Simulink.slx";
model_name = "Simulink";

load_system(model_file);

sim_input = Simulink.SimulationInput(model_name);
sim_input = sim_input.setVariable("Kp", Kp);
sim_input = sim_input.setVariable("Ti", Ti);
sim_input = sim_input.setVariable("Td", Td);
sim_input = sim_input.setVariable("Tf", Tf);
sim_input = sim_input.setVariable("filter", filter);
sim_input = sim_input.setVariable("plant", plant);
sim_input = sim_input.setVariable("constraint", constraint);
sim_input = sim_input.setModelParameter("StartTime", num2str(default_start_time));
sim_input = sim_input.setModelParameter("StopTime", num2str(default_end_time));
sim_input = sim_input.setModelParameter("SolverType", "Fixed-step");
sim_input = sim_input.setModelParameter("Solver", "ode4");
sim_input = sim_input.setModelParameter("FixedStep", num2str(default_time_step));

sim_output = sim(sim_input);
simout = sim_output.simout;

t_clamping = simout.time;
x_clamping = simout.signals.values;
r_clamping = ones(size(t_clamping));

figure;
plot(t_clamping, x_clamping);
grid on;
title('Simulink');
xlabel('t');
ylabel('y(t)');

figure;
plot(t_clamping, r_clamping, '--', 'LineWidth', 1.0);
hold on;
plot(t_clamping, x_clamping, 'LineWidth', 1.2);
grid on;
title('Sprungantwort');
xlabel('t');
ylabel('y(t)');
legend('r(t)', 'y(t)', 'Location', 'best');

ITAE_clamping = 0;
t_alt = 0;
for r = 1:length(t_clamping)
    delta_t = t_clamping(r) - t_alt;
    ITAE_clamping = ITAE_clamping + t_clamping(r) * abs((1 - x_clamping(r)) * delta_t);
    t_alt = t_clamping(r);
end

ITAE_clamping

close_system(model_name, 0);
