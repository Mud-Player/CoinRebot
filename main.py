from PySide6 import QtWidgets


import sys


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationName("Coin Robot")

    from MainWindow import MainWindow
    widget = MainWindow()
    widget.resize(1080, 720)
    widget.show()

    sys.exit(app.exec())
