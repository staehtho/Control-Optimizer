from app_domain.controlsys import ExcitationTarget

# TODO: Evaluation tab erst nach erstem PSO
# TODO: start und endzeit von evaluation im plot verbinden
# TODO: legende von plot ausserhalb
# TODO: Stellgrösse als subplot -> PlotWidget subplot
# TODO: BodePlot von PlotWidget erben oder ein BasePlotWidget?
# TODO: SettingsView


if __name__ == '__main__':
    name = ExcitationTarget.REFERENCE.name
    print(ExcitationTarget[name])
