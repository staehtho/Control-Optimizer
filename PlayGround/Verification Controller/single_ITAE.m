clear
clc
close all

s = tf('s');

% --------------------------------------------------
% Controller parameters
% --------------------------------------------------
pid_params = struct( ...
    "Kp", 0.999914491680377, ...
    "Ti", 0.6190286570861683, ...
    "Td", 2.1164430561740892, ...
    "Tf",  0.423289, ...
    "Kff", 0.0 ...
);

ffpid_params = struct( ...
    "Kp", 0.919382491084695, ...
    "Ti", 8.276388149048293, ...
    "Td", 1.8495056268734298, ...
    "Tf", 0.369901, ...
    "Kff", 0.9915320928353482 ...
);

filterPID = s / (pid_params.Tf * s + 1);
filterFFPID = s / (ffpid_params.Tf * s + 1);

% --------------------------------------------------
% Common simulation settings
% --------------------------------------------------
constraint = 100;
plant = tf(1, [1 0.2 1]);

default_start_time = 0.0;
default_end_time = 10.0;
default_time_step = 1e-4;

sim_cfg = struct( ...
    "plant", plant, ...
    "constraint", constraint, ...
    "start_time", default_start_time, ...
    "end_time", default_end_time, ...
    "time_step", default_time_step ...
);

% --------------------------------------------------
% Run both models
% --------------------------------------------------
pid_result = run_model_case("PID.slx", pid_params, filterPID, "filterPID", sim_cfg);
ffpid_result = run_model_case("FFPID.slx", ffpid_params, filterFFPID, "filterFFPID", sim_cfg);

fprintf("\nITAE results\n");
fprintf("------------\n");
fprintf("PID:   %.10f\n", pid_result.ITAE);
fprintf("FFPID: %.10f\n", ffpid_result.ITAE);

figure;
plot(pid_result.t, pid_result.r, '--', 'LineWidth', 1.0, 'DisplayName', 'r(t)');
hold on;
plot(pid_result.t, pid_result.y, 'LineWidth', 1.2, 'DisplayName', 'PID');
plot(ffpid_result.t, ffpid_result.y, 'LineWidth', 1.2, 'DisplayName', 'FFPID');
grid on;
title('Step response comparison');
xlabel('t');
ylabel('y(t)');
legend('Location', 'best');


function result = run_model_case(model_file, controller_params, filter_tf, filter_variable_name, sim_cfg)
    model_name = erase(model_file, ".slx");

    load_system(model_file);

    sim_input = Simulink.SimulationInput(model_name);
    sim_input = sim_input.setVariable("Kp", controller_params.Kp);
    sim_input = sim_input.setVariable("Ti", controller_params.Ti);
    sim_input = sim_input.setVariable("Td", controller_params.Td);
    sim_input = sim_input.setVariable("Tf", controller_params.Tf);
    sim_input = sim_input.setVariable("Kff", controller_params.Kff);
    sim_input = sim_input.setVariable("filter", filter_tf);
    sim_input = sim_input.setVariable(filter_variable_name, filter_tf);
    sim_input = sim_input.setVariable("plant", sim_cfg.plant);
    sim_input = sim_input.setVariable("constraint", sim_cfg.constraint);
    sim_input = sim_input.setModelParameter("StartTime", num2str(sim_cfg.start_time));
    sim_input = sim_input.setModelParameter("StopTime", num2str(sim_cfg.end_time));
    sim_input = sim_input.setModelParameter("SolverType", "Fixed-step");
    sim_input = sim_input.setModelParameter("Solver", "ode4");
    sim_input = sim_input.setModelParameter("FixedStep", num2str(sim_cfg.time_step));

    sim_output = sim(sim_input);
    simout = sim_output.simout;

    t = simout.time;
    y = simout.signals.values;
    r = ones(size(t));
    e = r - y;
    itae = trapz(t, t .* abs(e));

    result = struct( ...
        "model_name", model_name, ...
        "t", t, ...
        "y", y, ...
        "r", r, ...
        "ITAE", itae ...
    );

    close_system(model_name, 0);
end
