from PyQt5.QtCore import *
from datetime import datetime

class Real(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.flag = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_real_data)
        self.timer.start(1000)


    def update_real_data(self):
        try:

            for code in self.parent.rg_code:
                # 1초
                if len(self.parent.real_data[code]) == 3:
                    self.parent.real_data[code].pop(0)

                # 2초(이전에 수집된 경우는 건너뛰는 로직 self.flag 활용
                if len(self.parent.real_data2[code]) == 3 and self.flag:
                    self.parent.real_data2[code].pop(0)


                # 아직 데이터 수집 시작이 안된 경우 수집 X (거의 없을 듯)
                if self.parent.data[code]:
                    self.parent.real_data[code].append(self.parent.data[code])

                if self.parent.data[code] and self.flag:
                    self.parent.real_data2[code].append(self.parent.data[code])


            if self.flag:
                self.flag = False
            else:
                self.flag = True

        except Exception as e:
            pass