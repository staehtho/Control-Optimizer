import matplotlib.pyplot as plt
import numpy as np
from matplotlib.pyplot import figure

# TODO: Evaluation tab erst nach erstem PSO
# TODO: BodePlot von PlotWidget erben oder ein BasePlotWidget?
# TODO: SettingsView
# TODO: Title bereinigen


if __name__ == '__main__':
    x = np.arange(0, 10, 0.1)
    fig = plt.figure()

    y = [np.sin(x), np.cos(x)]
    ax = [fig.add_subplot(2, 1, i) for i in range(1, 3)]

    for i in range(len(y)):
        ax[i].plot(x, y[i])

    y = [np.cos(x), -np.sin(x)]

    for i in range(len(y)):
        ax[i].plot(x, y[i])

    ax[0].set_xlabel('x')
    ax[0].set_ylabel('y')
    ax[0].legend(['x', 'y'])
    ax[1].set_xlabel('x')
    ax[1].set_ylabel('y')
    ax[1].legend(['x', 'y'])
    ax[0].set_title("45asdf sdfasf adfasf")
    ax[1].set_title("45asdf sdfasf adfasf")

    fig.suptitle("123")

    plt.show()
