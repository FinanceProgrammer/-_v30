from PyQt5.QtCore import *
from datetime import datetime, timedelta
import pandas as pd

class Vi(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.vi_data)
        self.timer.start(1000)

    def vi_data(self):
        try:
        # 매분 10초에 검증
            if datetime.today().strftime("%S") == "10":
                t_1 = (datetime.today() - timedelta(minutes=1)).strftime("%Y%m%d%H%M%S")
                for info in self.parent.alarm_data:
                    data = info['분봉데이터']
                    t_1 = t_1[:-2]+"00"

                    if int(t_1) not in list(data['시간']):
                        lower_rows = data[data['시간'] < int(t_1)]
                        base_row = lower_rows.iloc[0]
                        new_row = {
                            '시간': int(t_1),
                            '시가': base_row['종가'],
                            '고가': base_row['종가'],
                            '저가': base_row['종가'],
                            '종가': base_row['종가'],
                            '거래량': 0
                            }
                        df = pd.concat([pd.DataFrame([new_row]), data], ignore_index=True)
                        df = df.sort_values(by='시간', ascending=False).reset_index(drop=True)
                        info['분봉데이터'] = df

        except Exception as e:
            print(e)