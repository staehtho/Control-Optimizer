
# TODO: Performance untersuchen / verbessern
# TODO: PA mit BA verglichen -> nicht kaput gemacht :) (Anti-Windup)
# TODO: evtl. im Bericht im theorieteil zeigen, wie totzeit in UTF approximiert werden kann, da wir nur UTF darstellen können
#   (System identifikation, Totzeit in LTI überführen)
# TODO: Frequenzbereich in app fixiert? e-5 bis e5?
# TODO: Auflösung im Frequenzbereich diskutieren


# TODO: Verhalten, wenn keine feasible Lösung gefunden werden kann  -> neuer Frame in PSOResult an erster stelle -> Rot Error:...
#   auch in Report an erster Stelle
# TODO: evt hyperparameter von PSO in systemsettings integrieren? -> gute Idee, wenn ja nur mit ToolTip
# TODO: Wo ist die automatische Simulationszeit in App -> ok ich verstehe wo (PSO Parameters -> Endtime) somit kann die
#   Endzeit und Start zeit automatisch bestummen werden -> Startzeit dann auf 0s -> Aufwand abschätzen
# TODO: Plots in App zu gross wenn in fullscreen -> alles in die linke obere Ecke rechts frei
# TODO: Controller Type in controller wirkt etwas komisch -> neue Section Controller Type und in dieser PID

# TODO: Report generierung: es ist keine Warnung vorhanden, das der Report schon existiert, und wenn er offen is kann er nicht erstellt werden und nicht .json!!!
# TODO: Export und Import: Brows durch Import / Export ersetzen nach speichern im Dialog wird exportiert oder importiert
# TODO: Report: Funktion aufführen
# TODO: Rheinfolge constraint max und min
# TODO: PSOResult: Anstelle von @ -> at oder bei
# TODO: TimeDomain Legend: Plant, y ClosedLoop r Referenc oder r / l und u Control Signal
# TODO: BodePlot es ist schon in rad/s einfach Beschriftung anpassen
# TODO: Titel von Plot raus