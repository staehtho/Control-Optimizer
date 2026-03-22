clear
clc
close all

s = tf('s');

Kp = 10;
Ti = 9.5608;
Td = 0.2972;
Tf = 0.01;
filter = s / ( Tf * s + 1); 
ka = 1/10;

sim('Vorlage_clamping')

t_clamping = simout.time;
x_clamping = simout.signals.values;

figure;
plot(t_clamping, x_clamping);
grid on;
title('Vorlage clamping');
xlabel('t');
ylabel('y(t)');

ITAE_clamping = 0;
t_alt = 0;
for r = 1:length(t_clamping)
    delta_t = t_clamping(r) - t_alt;
    ITAE_clamping = ITAE_clamping + t_clamping(r) * abs((1 - x_clamping(r)) * delta_t);
    t_alt = t_clamping(r);
end

ITAE_clamping

sim('Vorlage_backcalc')

t_backcalc = simout.time;
x_backcalc = simout.signals.values;

figure;
plot(t_backcalc, x_backcalc);
grid on;
title('Vorlage backcalc');
xlabel('t');
ylabel('y(t)');

ITAE_backcalc = 0;
t_alt = 0;
for r = 1:length(t_backcalc)
    delta_t = t_backcalc(r) - t_alt;
    ITAE_backcalc = ITAE_backcalc + t_backcalc(r) * abs((1 - x_backcalc(r)) * delta_t);
    t_alt = t_backcalc(r);
end

ITAE_backcalc
