import sys
from PyQt5.QtWidgets import QApplication
from mainWindow import ObstacleEditor


def main():
    app = QApplication(sys.argv)
    editor = ObstacleEditor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()