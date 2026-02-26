% Compute_Margins_All_consistent_sorted.m
% Ordnung:
%   PT2: D aufsteigend (0..1), innerhalb D: Stellgrenze 10,5,3,2
%   PTn: n aufsteigend (1..6), innerhalb n: Stellgrenze 10,5,3,2
%
% Kennwerte:
%   - PM (Phasenreserve), GM (Amplitudenreserve), omega_c (= Wcp)
%   - Ms = max|S(jw)|, S=1/(1+L)
%   - Tf aus dominantem Pol der STRECKE, 100x schneller

clear; clc;
s = tf('s');

% Frequenzgitter fuer Ms
w = logspace(-4, 4, 4000);

% Stellgroessen-Grenzen in deiner Reihenfolge:
u_abs_list = [10 5 3 2];

% Mapping: in den Parametertabellen ist j=1..4 als [2,3,5,10] gespeichert.
% Wir wollen [10,5,3,2] -> j = [4,3,2,1]
j_for_uabs = containers.Map( ...
    {'10','5','3','2'}, ...
    {4,   3,  2,  1} );

% Tf clamp (nur Sicherheitsnetz)
Tf_min = 1e-6;
Tf_max = 1e6;

%% =========================================================
% PT2: D-Order aus File -> wir mappen auf D aufsteigend
%% =========================================================
run('PT2_parameter_PSO.m');   % liefert pid_params{1..9,1..4}

% D-Reihenfolge wie im File (Kommentarstruktur):
D_src = [1.0 0.7 0.6 0.5 0.4 0.3 0.2 0.1 0.0];
D_out = sort(D_src); % [0..1] aufsteigend

rows = {};
for ii = 1:numel(D_out)
    D = D_out(ii);

    % i-Index im pid_params finden, der zu diesem D gehoert
    i = find(abs(D_src - D) < 1e-12, 1);
    if isempty(i)
        error("D=%g nicht in D_src gefunden. Prüfe D_src.", D);
    end

    % Strecke
    G = 1/(s^2 + 2*D*s + 1);

    % Tf aus dominantem Pol der Strecke
    Tf = local_Tf_from_plant(G, Tf_min, Tf_max);

    % innerhalb D: 10,5,3,2
    for kk = 1:numel(u_abs_list)
        uabs = u_abs_list(kk);
        j = j_for_uabs(num2str(uabs));  % korrektes j fuer diese Grenze

        u_min = -uabs;
        u_max =  uabs;

        Kp = pid_params{i,j}(1);
        Tn = pid_params{i,j}(2);
        Tv = pid_params{i,j}(3);

        Ki = Kp/Tn;
        Kd = Kp*Tv;

        C = pid(Kp, Ki, Kd, Tf);   % D-Filter integriert
        L = minreal(C*G);

        [GM, PM, ~, Wcp] = margin(L);
        GM_dB = 20*log10(GM);
        omega_c = Wcp;

        S = feedback(1, L);
        magS = squeeze(bode(S, w));
        [Ms, idx] = max(magS);
        wMs = w(idx);

        rows(end+1,:) = { ...
            "PT2", D, u_min, u_max, ...
            Kp, Tn, Tv, Tf, ...
            GM, GM_dB, PM, omega_c, Ms, wMs, ...
            i, j ...
        }; %#ok<SAGROW>
    end
end

T_PT2 = cell2table(rows, 'VariableNames', { ...
    'System','D','u_min','u_max', ...
    'Kp','Tn','Tv','Tf', ...
    'GM','GM_dB','PM_deg','omega_c','Ms','wMs', ...
    'idx_i_fromFile','idx_j_fromFile' ...
});

%% =========================================================
% PTn: n aufsteigend (1..6), innerhalb n: 10,5,3,2
%% =========================================================
run('PTn_parameter_PSO.m');   % liefert pid_params{n,j}, n=1..6

rows = {};
for n = 1:6
    G = 1/(s+1)^n;
    Tf = local_Tf_from_plant(G, Tf_min, Tf_max);

    for kk = 1:numel(u_abs_list)
        uabs = u_abs_list(kk);
        j = j_for_uabs(num2str(uabs));

        u_min = -uabs;
        u_max =  uabs;

        Kp = pid_params{n,j}(1);
        Tn = pid_params{n,j}(2);
        Tv = pid_params{n,j}(3);

        Ki = Kp/Tn;
        Kd = Kp*Tv;

        C = pid(Kp, Ki, Kd, Tf);
        L = minreal(C*G);

        [GM, PM, ~, Wcp] = margin(L);
        GM_dB = 20*log10(GM);
        omega_c = Wcp;

        S = feedback(1, L);
        magS = squeeze(bode(S, w));
        [Ms, idx] = max(magS);
        wMs = w(idx);

        rows(end+1,:) = { ...
            "PTn", n, u_min, u_max, ...
            Kp, Tn, Tv, Tf, ...
            GM, GM_dB, PM, omega_c, Ms, wMs, ...
            n, j ...
        }; %#ok<SAGROW>
    end
end

T_PTn = cell2table(rows, 'VariableNames', { ...
    'System','n','u_min','u_max', ...
    'Kp','Tn','Tv','Tf', ...
    'GM','GM_dB','PM_deg','omega_c','Ms','wMs', ...
    'idx_n_fromFile','idx_j_fromFile' ...
});

%% =========================================================
% Export
%% =========================================================
disp('=== PT2 (D aufsteigend, u=10,5,3,2) ==='); disp(T_PT2);
disp('=== PTn (n aufsteigend, u=10,5,3,2) ==='); disp(T_PTn);

writetable(T_PT2, 'Margins_PT2_Matlab.csv');
writetable(T_PTn, 'Margins_PTn_Matlab.csv');
save('Margins_All_sorted_consistent.mat', 'T_PT2', 'T_PTn');

%% =========================================================
% Tf aus dominantem Pol der Strecke
% - "dominant": Pol mit groesstem Realteil (nahe 0)
% - tau = -1/real(p) wenn real(p)<0
% - Sonderfall real(p)~0 (z.B. D=0): tau = 1/|p|
%% =========================================================
function Tf = local_Tf_from_plant(G, Tf_min, Tf_max)
    p = pole(G);

    % dominant = groesster Realteil
    [~, idx] = max(real(p));
    p_dom = p(idx);

    if real(p_dom) < -1e-12
        tau = -1/real(p_dom);
    else
        % marginal/nahe imaginär: benutze Betrag (z.B. p = +-j*wn)
        tau = 1/max(abs(p_dom), 1e-12);
    end

    Tf = tau/100;
    Tf = min(max(Tf, Tf_min), Tf_max);
end