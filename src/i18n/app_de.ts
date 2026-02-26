<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de_DE">
<context>
    <name>ControlEnums</name>
    <message>
        <location filename="../views/translations/enum_translations.py" line="50"/>
        <source>Clamping</source>
        <translation>Clamping</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="51"/>
        <source>Conditional</source>
        <translation>Conditional</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="58"/>
        <source>Reference</source>
        <translation>Führung</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="59"/>
        <source>Input Disturbance</source>
        <translation>Eingangsstörung</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="60"/>
        <source>Measurement Disturbance</source>
        <translation>Messstörung</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="68"/>
        <source>ITAE</source>
        <translation>ITAE</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="69"/>
        <source>IAE</source>
        <translation>IAE</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="70"/>
        <source>ITSE</source>
        <translation>ITSE</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="71"/>
        <source>ISE</source>
        <translation>ISE</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="78"/>
        <source>step</source>
        <translation>Sprungfunktion</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="79"/>
        <source>sine</source>
        <translation>Sinusfunktion</translation>
    </message>
    <message>
        <location filename="../views/translations/enum_translations.py" line="80"/>
        <source>cosine</source>
        <translation>Kosinusfunktion</translation>
    </message>
</context>
<context>
    <name>ControllerView</name>
    <message>
        <location filename="../views/controller_view.py" line="91"/>
        <source>Controller</source>
        <translation>Regler</translation>
    </message>
    <message>
        <location filename="../views/controller_view.py" line="94"/>
        <source>Controller Type</source>
        <translation>Reglertyp</translation>
    </message>
    <message>
        <location filename="../views/controller_view.py" line="95"/>
        <source>Anti Windup</source>
        <translation>Windup</translation>
    </message>
    <message>
        <location filename="../views/controller_view.py" line="96"/>
        <source>Constraint</source>
        <translation>Begrenzung</translation>
    </message>
    <message>
        <location filename="../views/controller_view.py" line="97"/>
        <source>Minimum</source>
        <translation>Minimum</translation>
    </message>
    <message>
        <location filename="../views/controller_view.py" line="98"/>
        <source>Maximum</source>
        <translation>Maximum</translation>
    </message>
</context>
<context>
    <name>Function</name>
    <message>
        <source>Cosine function</source>
        <translation type="vanished">Kosinusfunktion</translation>
    </message>
    <message>
        <source>Sine function</source>
        <translation type="vanished">Sinusfunktion</translation>
    </message>
    <message>
        <source>Step function</source>
        <translation type="vanished">Sprungfunktion</translation>
    </message>
    <message>
        <location filename="../views/function_view.py" line="77"/>
        <source>Time [s]</source>
        <translation>Zeit [s]</translation>
    </message>
    <message>
        <location filename="../views/function_view.py" line="78"/>
        <source>Output</source>
        <translation>Ausgang</translation>
    </message>
</context>
<context>
    <name>FunctionModel</name>
    <message>
        <source>Unit step function</source>
        <translation type="vanished">Einheitssprung</translation>
    </message>
    <message>
        <source>Sine function</source>
        <translation type="vanished">Sinusfunktion</translation>
    </message>
    <message>
        <source>Cosine function</source>
        <translation type="vanished">Kosinusfunktion</translation>
    </message>
    <message>
        <source>Time [s]</source>
        <translation type="vanished">Zeit [s]</translation>
    </message>
    <message>
        <source>Output</source>
        <translation type="vanished">Ausgang</translation>
    </message>
</context>
<context>
    <name>FunctionView</name>
    <message>
        <location filename="../views/function_view.py" line="177"/>
        <source>Excitation Function</source>
        <translation>Anregungsfunktion</translation>
    </message>
</context>
<context>
    <name>PlantView</name>
    <message>
        <location filename="../views/plant_view.py" line="64"/>
        <location filename="../views/plant_view.py" line="164"/>
        <source>plant.num</source>
        <translation>Nenner</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="78"/>
        <location filename="../views/plant_view.py" line="165"/>
        <source>plant.den</source>
        <translation>Zähler</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="163"/>
        <source>Plant</source>
        <translation>Regelstrecke</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="166"/>
        <source>e.g. 1  → 1</source>
        <translation>z.B. 1  → 1</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="167"/>
        <source>e.g. 1, 0, 0  → 1*s^2 + 0*s + 0</source>
        <translation>z.B. 1, 0, 0  → 1*s² + 0*s + 0</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="169"/>
        <source>tooltip_num_den</source>
        <translation>Verwenden Sie „.“ als Dezimaltrennzeichen.
Die erste Zahl entspricht der höchsten Potenz von s.
Beispiel: 1, 0.5, 2 → 1·s² + 0,5·s + 2</translation>
    </message>
    <message>
        <source>Enter coefficients separated by commas, spaces, or semicolons.
Use &apos;.&apos; as the decimal point.
The first number corresponds to the highest power of s.
Example: 1, 0.5, 2 → 1*s^2 + 0.5*s + 2</source>
        <translation type="vanished">Verwenden Sie „.“ als Dezimaltrennzeichen.
Die erste Zahl entspricht der höchsten Potenz von s.
Beispiel: 1, 0.5, 2 → 1·s² + 0,5·s + 2</translation>
    </message>
</context>
<context>
    <name>PlotView</name>
    <message>
        <location filename="../views/plot_view.py" line="121"/>
        <source>plot.grid</source>
        <translation>Grid</translation>
    </message>
    <message>
        <location filename="../views/plot_view.py" line="122"/>
        <source>plot.start</source>
        <translation>Startzeit</translation>
    </message>
    <message>
        <location filename="../views/plot_view.py" line="123"/>
        <source>plot.end</source>
        <translation>Endzeit</translation>
    </message>
    <message>
        <location filename="../views/plot_view.py" line="124"/>
        <source>plot.start.tooltip</source>
        <translation>Untere Grenze der x-Achse (x_min).
Legt fest, wo die Zeitachse beginnt.
Einheit: Sekunden (s).</translation>
    </message>
    <message>
        <location filename="../views/plot_view.py" line="125"/>
        <source>plot.end.tooltip</source>
        <translation>Obere Grenze der x-Achse (x_max).
Legt fest, wo die Zeitachse endet.
Einheit: Sekunden (s).
Muss grösser als die Startzeit sein.</translation>
    </message>
</context>
<context>
    <name>PsoConfigurationView</name>
    <message>
        <source>PSO Bounds</source>
        <translation type="vanished">PSO Grenzen</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="218"/>
        <source>Excitation Function</source>
        <translation>Anregungsfunktion</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="223"/>
        <source>Simulation Time</source>
        <translation>Simulationszeit</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="224"/>
        <source>Start Time</source>
        <translation>Startzeit</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="225"/>
        <source>End Time</source>
        <translation>Endzeit</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="226"/>
        <source>Excitation Target</source>
        <translation>Anregungsfunktion</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="228"/>
        <source>Time Domain</source>
        <translation>Zeitbereich</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="229"/>
        <source>PSO Bounds: Kp</source>
        <translation>PSO Grenze Kp</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="232"/>
        <source>PSO Bounds: Ti</source>
        <translation>PSO Grenze Ti</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="235"/>
        <source>PSO Bounds: Td</source>
        <translation>PSO Grenze Td</translation>
    </message>
    <message>
        <source>Anti-Windup Strategy</source>
        <translation type="vanished">Anti-Windup</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="227"/>
        <source>Performance Index</source>
        <translation>Gütekriterium</translation>
    </message>
    <message>
        <source>Constraint</source>
        <translation type="vanished">Begrenzung</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="230"/>
        <location filename="../views/pso_configuration_view.py" line="233"/>
        <location filename="../views/pso_configuration_view.py" line="236"/>
        <source>Minimum</source>
        <translation>Minimum</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="231"/>
        <location filename="../views/pso_configuration_view.py" line="234"/>
        <location filename="../views/pso_configuration_view.py" line="237"/>
        <source>Maximum</source>
        <translation>Maximum</translation>
    </message>
    <message>
        <source>Kp</source>
        <translation type="vanished">Kp</translation>
    </message>
    <message>
        <source>Ti</source>
        <translation type="vanished">Ti</translation>
    </message>
    <message>
        <source>Td</source>
        <translation type="vanished">Td</translation>
    </message>
    <message>
        <source>Reference</source>
        <translation type="vanished">Führung</translation>
    </message>
    <message>
        <source>Input Disturbance</source>
        <translation type="vanished">Eingangsstörung</translation>
    </message>
    <message>
        <source>Measurement Disturbance</source>
        <translation type="vanished">Messstörung</translation>
    </message>
    <message>
        <source>Clamping</source>
        <translation type="vanished">Clamping</translation>
    </message>
    <message>
        <source>Conditional</source>
        <translation type="vanished">Conditional</translation>
    </message>
    <message>
        <source>ITAE</source>
        <translation type="vanished">ITAE</translation>
    </message>
    <message>
        <source>IAE</source>
        <translation type="vanished">IAE</translation>
    </message>
    <message>
        <source>ITSE</source>
        <translation type="vanished">ITSE</translation>
    </message>
    <message>
        <source>ISE</source>
        <translation type="vanished">ISE</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="217"/>
        <source>Plant</source>
        <translation>Regelstrecke</translation>
    </message>
    <message>
        <location filename="../views/pso_configuration_view.py" line="219"/>
        <source>Controller Optimization Parameters</source>
        <translation>Parameter zur Optimierung des Reglers</translation>
    </message>
    <message>
        <source>title.plant</source>
        <translation type="vanished">Regelstrecke</translation>
    </message>
    <message>
        <source>title.control</source>
        <translation type="vanished">Parameter zur Optimierung des Reglers</translation>
    </message>
    <message>
        <source>control.start_time</source>
        <translation type="vanished">Startzeit</translation>
    </message>
    <message>
        <source>control.end_time</source>
        <translation type="vanished">Endzeit</translation>
    </message>
    <message>
        <source>control.anti_windup</source>
        <translation type="vanished">Anti Windup</translation>
    </message>
    <message>
        <source>control.excitation_target</source>
        <translation type="vanished">Anregungsfunktion</translation>
    </message>
    <message>
        <source>control.performance_index</source>
        <translation type="vanished">Gütekriterium</translation>
    </message>
    <message>
        <source>control.constraint_min</source>
        <translation type="vanished">untere Begrenzung</translation>
    </message>
    <message>
        <source>control.constraint_max</source>
        <translation type="vanished">obere Begrenzung</translation>
    </message>
</context>
<context>
    <name>plant.view</name>
    <message>
        <location filename="../views/plant_view.py" line="125"/>
        <source>Step Response</source>
        <translation>Sprungantwort</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="126"/>
        <source>Time [s]</source>
        <translation>Zeit [s]</translation>
    </message>
    <message>
        <location filename="../views/plant_view.py" line="127"/>
        <source>Output</source>
        <translation>Ausgang</translation>
    </message>
</context>
</TS>
