import sys

from PyQt6.QtWidgets import QApplication

from ui.app import App

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    main = App()
    sys.exit(app.exec())
