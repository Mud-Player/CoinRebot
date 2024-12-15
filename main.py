from PySide6 import QtWidgets

from MainWindow import MainWindow

import sys


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationName("Coin Rebot")

    widget = MainWindow()
    widget.resize(1080, 720)
    widget.show()

    sys.exit(app.exec())
