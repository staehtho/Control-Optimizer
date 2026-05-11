clear;
clc;
close all;

cfg = build_demo_config();
cases = build_demo_cases();
results = repmat(empty_result_struct(), numel(cases), 1);

for k = 1:numel(cases)
    results(k) = evaluate_case(cfg, cases(k));
end

names = strings(numel(results), 1);
for k = 1:numel(results)
    names(k) = string(results(k).name);
end

summary_table = table( ...
    names, ...
    reshape([results.Kp], [], 1), ...
    reshape([results.Ti], [], 1), ...
    reshape([results.Td], [], 1), ...
    reshape([results.Tf], [], 1), ...
    reshape([results.ITAE], [], 1), ...
    reshape([results.final_y], [], 1), ...
    'VariableNames', {'name', 'Kp', 'Ti', 'Td', 'Tf', 'ITAE', 'final_y'});
disp(summary_table);

plot_open_loops(results, cfg);
plot_step_responses(results, cfg);

if cfg.save_summary_csv
    writetable(summary_table, fullfile(cfg.output_dir, "optimierungsdemonstration_summary.csv"));
end

if bdIsLoaded(cfg.model_name)
    close_system(cfg.model_name, 0);
end


function cfg = build_demo_config()
    [script_dir, model_file] = resolve_demo_paths();
    [model_dir, model_base, ~] = fileparts(model_file);

    cfg.output_dir = script_dir;
    cfg.model_dir = model_dir;
    cfg.model_file = model_file;
    cfg.model_name = string(model_base);

    % PTn reference convention used in the project:
    % PT3 => G(s) = 1 / (s + 1)^3
    cfg.plant_num = 1.0;
    cfg.plant_den = [1.0, 3.0, 3.0, 1.0];

    cfg.t0 = 0.0;
    cfg.t1 = 10.0;
    cfg.dt = 1e-4;

    cfg.constraint = 5.0;
    cfg.reference = 1.0;

    cfg.omega = logspace(-2, 2, 1600);

    cfg.save_open_loop_figure = false;
    cfg.save_step_figure = false;
    cfg.save_summary_csv = false;
end


function [script_dir, model_file] = resolve_demo_paths()
    candidate_dirs = {};

    if usejava("desktop")
        active_file = matlab.desktop.editor.getActiveFilename;
        if ~isempty(active_file)
            candidate_dirs{end + 1} = fileparts(active_file); %#ok<AGROW>
        end
    end

    which_self = which(mfilename);
    if ~isempty(which_self)
        candidate_dirs{end + 1} = fileparts(which_self); %#ok<AGROW>
    end

    fullpath_self = mfilename("fullpath");
    if ~isempty(fullpath_self)
        candidate_dirs{end + 1} = fileparts(fullpath_self); %#ok<AGROW>
    end

    candidate_dirs{end + 1} = pwd; %#ok<AGROW>

    search_roots = unique(candidate_dirs, "stable");
    for k = 1:numel(search_roots)
        candidate_model = fullfile(search_roots{k}, "Simulink.slx");
        if isfile(candidate_model)
            script_dir = search_roots{k};
            model_file = candidate_model;
            return;
        end
    end

    error("Simulink.slx wurde nicht gefunden. Erwartet im Skriptordner oder im aktuellen Arbeitsverzeichnis.");
end


function cases = build_demo_cases()
    cases = [ ...
        struct("name", "ohne NB",           "label", "ohne NB",             "itae_doc", 1.27, "Kp", 3.21, "Ti", 4.04, "Td", 0.730, "Tf", 0.146), ...
        struct("name", "os = 0",            "label", "os = 0",              "itae_doc", 1.40, "Kp", 2.83, "Ti", 3.89, "Td", 0.761, "Tf", 0.152), ...
        struct("name", "du/dt = 10",        "label", "du/dt = 10",          "itae_doc", 1.34, "Kp", 4.70, "Ti", 5.55, "Td", 0.700, "Tf", 0.140), ...
        struct("name", "g_m = 18 dB",       "label", "g_m = 18 dB",         "itae_doc", 1.34, "Kp", 2.42, "Ti", 3.25, "Td", 0.690, "Tf", 0.138), ...
        struct("name", "varphi_m = 70 deg", "label", "phi_m = 70 deg", "itae_doc", 1.44, "Kp", 2.02, "Ti", 2.88, "Td", 0.717, "Tf", 0.143), ...
        struct("name", "S_max = 3 dB",      "label", "S_{max} = 3 dB",      "itae_doc", 1.40, "Kp", 2.12, "Ti", 2.95, "Td", 0.696, "Tf", 0.139)  ...
    ];
end


function result = empty_result_struct()
    result = struct( ...
        "name", "", ...
        "label", "", ...
        "itae_doc", NaN, ...
        "Kp", NaN, ...
        "Ti", NaN, ...
        "Td", NaN, ...
        "Tf", NaN, ...
        "ITAE", NaN, ...
        "final_y", NaN, ...
        "t", [], ...
        "y", [], ...
        "open_loop_tf", tf(1));
end


function result = evaluate_case(cfg, case_data)
    s = tf("s");
    plant_tf = tf(cfg.plant_num, cfg.plant_den);
    Tf = case_data.Tf;
    controller_tf = case_data.Kp * ...
        (1 + 1 / (case_data.Ti * s) + (case_data.Td * s) / (Tf * s + 1));
    open_loop_tf = controller_tf * plant_tf;
    [t, y] = simulate_closed_loop_simulink(cfg, case_data.Kp, case_data.Ti, case_data.Td, Tf, plant_tf);
    itae_value = compute_itae(t, y, cfg.reference);

    result = struct();
    result.name = string(case_data.name);
    result.label = string(case_data.label);
    result.itae_doc = case_data.itae_doc;
    result.Kp = case_data.Kp;
    result.Ti = case_data.Ti;
    result.Td = case_data.Td;
    result.Tf = Tf;
    result.ITAE = itae_value;
    result.final_y = y(end);
    result.t = t;
    result.y = y;
    result.open_loop_tf = open_loop_tf;
end


function [t, y_hist] = simulate_closed_loop_simulink(cfg, Kp, Ti, Td, Tf, plant_tf)
    s = tf("s");
    filter = s / (Tf * s + 1);

    if ~bdIsLoaded(cfg.model_name)
        old_dir = pwd;
        cleanup_obj = onCleanup(@() cd(old_dir)); %#ok<NASGU>
        cd(cfg.model_dir);
        load_system(char(cfg.model_name));
    end

    sim_input = Simulink.SimulationInput(cfg.model_name);
    sim_input = sim_input.setVariable("Kp", Kp);
    sim_input = sim_input.setVariable("Ti", Ti);
    sim_input = sim_input.setVariable("Td", Td);
    sim_input = sim_input.setVariable("Tf", Tf);
    sim_input = sim_input.setVariable("filter", filter);
    sim_input = sim_input.setVariable("plant", plant_tf);
    sim_input = sim_input.setVariable("constraint", cfg.constraint);
    sim_input = sim_input.setModelParameter("StartTime", num2str(cfg.t0));
    sim_input = sim_input.setModelParameter("StopTime", num2str(cfg.t1));
    sim_input = sim_input.setModelParameter("SolverType", "Fixed-step");
    sim_input = sim_input.setModelParameter("Solver", "ode4");
    sim_input = sim_input.setModelParameter("FixedStep", num2str(cfg.dt));

    sim_output = sim(sim_input);
    simout = sim_output.simout;

    t = simout.time;
    y_hist = simout.signals.values;
end


function val = compute_itae(t, y, r_final)
    val = 0.0;
    for k = 2:numel(t)
        val = val + t(k) * abs(r_final - y(k)) * (t(k) - t(k - 1));
    end
end


function plot_open_loops(results, cfg)
    fig = figure("Name", "Open-loop optimization demonstration", "Color", "w");
    tl = tiledlayout(fig, 2, 1);

    ax1 = nexttile(tl, 1);
    hold(ax1, "on");
    grid(ax1, "on");
    set(ax1, "XScale", "log");
    ylabel(ax1, "Magnitude [dB]");

    ax2 = nexttile(tl, 2);
    hold(ax2, "on");
    grid(ax2, "on");
    set(ax2, "XScale", "log");
    xlabel(ax2, "\omega [rad/s]");
    ylabel(ax2, "Phase [deg]");

    for k = 1:numel(results)
        resp = squeeze(freqresp(results(k).open_loop_tf, cfg.omega));
        mag_db = 20.0 * log10(abs(resp));
        phase_deg = unwrap(angle(resp)) * 180.0 / pi;

        semilogx(ax1, cfg.omega, mag_db, "LineWidth", 1.4, "DisplayName", results(k).label);
        semilogx(ax2, cfg.omega, phase_deg, "LineWidth", 1.4, "DisplayName", results(k).label);
    end

    legend(ax1, "Location", "best");
    xlim(ax1, [1e-2, 1e2]);
    xlim(ax2, [1e-2, 1e2]);

    if cfg.save_open_loop_figure
        exportgraphics(fig, fullfile(cfg.output_dir, "openloop_optimierung.png"), "Resolution", 200);
    end
end


function plot_step_responses(results, cfg)
    fig = figure("Name", "Step responses optimization demonstration", "Color", "w");
    ax = axes(fig);
    hold(ax, "on");
    grid(ax, "on");
    xlabel(ax, "t [s]");
    ylabel(ax, "y(t)");

    yline(ax, cfg.reference, "--", "Color", [0.3 0.3 0.3], "LineWidth", 1.0, "HandleVisibility", "off");

    response_handles = gobjects(numel(results), 1);
    for k = 1:numel(results)
        legend_label = sprintf("ITAE = %.2f, %s", results(k).itae_doc, char(results(k).label));
        response_handles(k) = plot(ax, results(k).t, results(k).y, "LineWidth", 1.4, "DisplayName", legend_label);
    end

    leg_main = legend(ax, response_handles, "Location", "best");
    set(leg_main, "Interpreter", "tex");

    if cfg.save_step_figure
        exportgraphics(fig, fullfile(cfg.output_dir, "stepresponse_optimierung.png"), "Resolution", 200);
    end
end
