from PyQt5.QtWidgets import *

class SectorSettingDialog(QDialog):
    def __init__(self, parent=None, init_settings=None):
        super().__init__(parent)
        self.setWindowTitle("섹터 설정")
        self.setGeometry(300, 300, 800, 400)

        self.sector_setting = init_settings if init_settings is not None else []

        # 콤보박스 항목
        self.buy_strategies = ["기본매수", "탄력매수"]
        self.sell_strategies = ["트레일링스탑", "5전환매도", "20전환매도", "교차매도", "복합매도", "스네이크셀", ""]
        self.sectors = ["고점형", "저점형", "중점형", "연속상승", "거래상승", "자유상승", "순위상승", "반등상승", "저점상승"]

        # 위젯 생성
        self.combo_buy = QComboBox()
        self.combo_buy.addItems(self.buy_strategies)

        self.combo_sell = QComboBox()
        self.combo_sell.addItems(self.sell_strategies)

        self.combo_sector = QComboBox()
        self.combo_sector.addItems(self.sectors)

        self.checkbox_market = QCheckBox("부정장")

        self.line_start_time = QLineEdit()
        self.line_end_time = QLineEdit()
        self.line_asset = QLineEdit()

        self.button_add = QPushButton("추가")
        self.button_add.clicked.connect(self.add_setting)

        self.button_confirm = QPushButton("확인")
        self.button_confirm.clicked.connect(self.confirm_settings)

        self.table_settings = QTableWidget(0, 8)
        self.table_settings.setHorizontalHeaderLabels(["삭제", "섹터명", "부정장", "시작시간", "종료시간", "자산할당%", "매수전략", "매도전략"])
        self.table_settings.verticalHeader().setVisible(False)
        self.table_settings.setColumnWidth(0, 40)

        # 레이아웃 구성
        layout_top = QHBoxLayout()
        layout_top.addWidget(QLabel("섹터명"))
        layout_top.addWidget(self.combo_sector)
        layout_top.addWidget(self.checkbox_market)
        layout_top.addWidget(QLabel("시작시간"))
        layout_top.addWidget(self.line_start_time)
        layout_top.addWidget(QLabel("종료시간"))
        layout_top.addWidget(self.line_end_time)
        layout_top.addWidget(QLabel("자산할당%"))
        layout_top.addWidget(self.line_asset)
        layout_top.addWidget(QLabel("매수전략"))
        layout_top.addWidget(self.combo_buy)
        layout_top.addWidget(QLabel("매도전략"))
        layout_top.addWidget(self.combo_sell)

        layout_main = QVBoxLayout()
        layout_main.addLayout(layout_top)
        layout_main.addWidget(self.button_add)
        layout_main.addWidget(QLabel("설정 리스트"))
        layout_main.addWidget(self.table_settings)
        layout_main.addWidget(self.button_confirm)

        self.setLayout(layout_main)
        self.refresh_table()

    def add_setting(self):
        sector = self.combo_sector.currentText()
        is_bear = self.checkbox_market.isChecked()
        start_time = self.line_start_time.text()
        end_time = self.line_end_time.text()
        asset = self.line_asset.text()
        buy = self.combo_buy.currentText()
        sell = self.combo_sell.currentText()

        # 유효성 검사
        try:
            start = int(start_time)
            end = int(end_time)
            asset_percent = float(asset)
            if not (900 <= start <= 2530) or not (900 <= end <= 2530):
                raise ValueError("시간 범위 오류")
            if not (0 <= asset_percent <= 100):
                raise ValueError("자산 비율 오류")
        except:
            QMessageBox.warning(self, "입력 오류", "시작/종료시간은 900~1530 사이, 자산할당은 0~100 사이로 입력해야 합니다.")
            return

        setting = {
            "섹터명": sector,
            "부정장": is_bear,
            "시작시간": start_time,
            "종료시간": end_time,
            "자산할당": asset,
            "매수전략": buy,
            "매도전략": sell
        }
        self.sector_setting.append(setting)
        self.refresh_table()

    def delete_setting(self, row):
        if 0 <= row < len(self.sector_setting):
            self.sector_setting.pop(row)
            self.refresh_table()

    def refresh_table(self):
        self.table_settings.setRowCount(0)
        for idx, setting in enumerate(self.sector_setting):
            self.table_settings.insertRow(idx)

            btn_delete = QPushButton("삭제")
            btn_delete.setMaximumWidth(40)
            btn_delete.clicked.connect(lambda _, r=idx: self.delete_setting(r))
            self.table_settings.setCellWidget(idx, 0, btn_delete)

            self.table_settings.setItem(idx, 1, QTableWidgetItem(setting["섹터명"]))
            self.table_settings.setItem(idx, 2, QTableWidgetItem('O' if setting["부정장"] else 'X'))
            self.table_settings.setItem(idx, 3, QTableWidgetItem(setting["시작시간"]))
            self.table_settings.setItem(idx, 4, QTableWidgetItem(setting["종료시간"]))
            self.table_settings.setItem(idx, 5, QTableWidgetItem(setting["자산할당"]))
            self.table_settings.setItem(idx, 6, QTableWidgetItem(setting["매수전략"]))
            self.table_settings.setItem(idx, 7, QTableWidgetItem(setting["매도전략"]))

    def confirm_settings(self):
        print("현재 설정 리스트:")
        for setting in self.sector_setting:
            print(setting)
        self.accept()

    def get_settings(self):
        return self.sector_setting