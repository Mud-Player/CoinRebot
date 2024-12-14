import sys

import PySide6.QtAsyncio as QtAsyncio
from PySide6 import QtWidgets

from MainWindow import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationName("BitgetBot")

    widget = MainWindow()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
