import sys
from PyQt5.QtWidgets import QApplication
from arayuz import AppWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AppWindow()
    pencere.show()
    sys.exit(app.exec_())