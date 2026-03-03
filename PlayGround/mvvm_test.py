from app_domain.controlsys import ExcitationTarget

# TODO: Evaluation tab erst nach erstem PSO
# TODO: Stellgrösse als subplot -> PlotWidget subplot
# TODO: BodePlot von PlotWidget erben oder ein BasePlotWidget?
# TODO: SettingsView


if __name__ == '__main__':
    name = ExcitationTarget.REFERENCE.name
    print(ExcitationTarget[name])
