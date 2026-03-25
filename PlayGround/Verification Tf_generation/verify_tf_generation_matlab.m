clear;
clc;
close all;

input_file = "batch_results_tf_generation.xlsx";
output_file = "batch_results_tf_generation_matlab.xlsx";
model_file = "Simulink.slx";
model_name = "Simulink";

default_start_time = 0.0;
default_end_time = 20.0;
default_time_step = 1e-4;
plot_first_case = false;

results = readtable(input_file);
row_count = height(results);

itae_matlab = zeros(row_count, 1);
itae_delta_vs_python = zeros(row_count, 1);
itae_delta_vs_reference = zeros(row_count, 1);

load_system(model_file);

for idx = 1:row_count
    system_type = string(results.type(idx));
    param_value = results.n_or_D(idx);
    amplitude_limit = results.A(idx);

    if ismember("time_step", results.Properties.VariableNames)
        dt = results.time_step(idx);
        if isnan(dt)
            dt = default_time_step;
        end
    else
        dt = default_time_step;
    end

    if ismember("start_time", results.Properties.VariableNames)
        t0 = results.start_time(idx);
        if isnan(t0)
            t0 = default_start_time;
        end
    else
        t0 = default_start_time;
    end

    if ismember("end_time", results.Properties.VariableNames)
        t1 = results.end_time(idx);
        if isnan(t1)
            t1 = default_end_time;
        end
    else
        t1 = default_end_time;
    end

    Kp = results.best_kp_new(idx);
    Ti = results.best_ti_new(idx);
    Td = results.best_td_new(idx);
    Tf = results.tf_new_effective(idx);

    plant = build_plant(system_type, param_value);
    filter = build_filter(Tf, Td);
    constraint = amplitude_limit;

    sim_input = Simulink.SimulationInput(model_name);
    sim_input = sim_input.setVariable("Kp", Kp);
    sim_input = sim_input.setVariable("Ti", Ti);
    sim_input = sim_input.setVariable("Td", Td);
    sim_input = sim_input.setVariable("filter", filter);
    sim_input = sim_input.setVariable("plant", plant);
    sim_input = sim_input.setVariable("constraint", constraint);
    sim_input = sim_input.setModelParameter("StartTime", num2str(t0));
    sim_input = sim_input.setModelParameter("StopTime", num2str(t1));
    sim_input = sim_input.setModelParameter("SolverType", "Fixed-step");
    sim_input = sim_input.setModelParameter("Solver", "ode4");
    sim_input = sim_input.setModelParameter("FixedStep", num2str(dt));

    sim_output = sim(sim_input);
    simout = sim_output.simout;

    t_eval = simout.time;
    y_hist = simout.signals.values;
    if size(y_hist, 2) > 1
        y_hist = y_hist(:, 1);
    end

    current_itae = compute_itae(t_eval, y_hist);

    itae_matlab(idx) = current_itae;
    itae_delta_vs_python(idx) = current_itae - results.itae_new(idx);
    itae_delta_vs_reference(idx) = current_itae - results.itae_reference(idx);

    if plot_first_case && idx == 1
        figure;
        plot(t_eval, y_hist, "LineWidth", 1.2);
        grid on;
        xlabel("t [s]");
        ylabel("y");
        title("Closed-loop response from Simulink");
    end
end

close_system(model_name, 0);

results.itae_matlab = itae_matlab;
results.itae_delta_vs_python = itae_delta_vs_python;
results.itae_delta_vs_reference = itae_delta_vs_reference;

writetable(results, output_file);

disp("MATLAB/Simulink verification finished.");
disp("Output written to: " + output_file);


function plant = build_plant(system_type, param_value)
    switch char(system_type)
        case 'PTn'
            order = round(param_value);
            denominator = 1.0;
            for k = 1:order
                denominator = conv(denominator, [1.0, 1.0]);
            end
            plant = tf(1.0, denominator);
        case 'PT2'
            damping = param_value;
            plant = tf(1.0, [1.0, 2.0 * damping, 1.0]);
        otherwise
            error("Unsupported system type: %s", system_type);
    end
end


function filter = build_filter(Tf, Td)
    if Td <= 0.0
        filter = tf(0.0, 1.0);
        return;
    end

    if Tf <= 0.0
        error("Tf must be > 0 when Td > 0.");
    end

    filter = tf([1.0, 0.0], [Tf, 1.0]);
end


function itae = compute_itae(t_eval, y_hist)
    itae = 0.0;
    for i = 2:length(t_eval)
        err = 1.0 - y_hist(i);
        dt_local = t_eval(i) - t_eval(i - 1);
        itae = itae + t_eval(i) * abs(err) * dt_local;
    end
end