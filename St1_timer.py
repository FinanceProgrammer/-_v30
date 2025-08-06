from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QDateTime

class st1(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def update_time(self):
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.parent.tw1.setItem(0, 0, QTableWidgetItem(current_time))