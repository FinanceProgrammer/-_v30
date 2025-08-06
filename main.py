import sys
from PyQt5 import uic
from St1_timer import *
from St3_telegram import *
from St import *
from setting import *
from real import *
from vi import *
from rv import *

form_class = uic.loadUiType("UI.ui")[0]
class Gui(QMainWindow, QWidget, form_class):

    def __init__(self, *args, **kwargs):
        super(Gui, self).__init__(*args, **kwargs)
        form_class.__init__(self)
        self.setUI()

        # self.test가 True면 토큰 api 등 개발자의 값 적용
        self.test = True
        self.flag = False
        self.first = True

        # 텔레그램에 전달된 메시지를 담아놓는 리스트
        # [{'시간': '091000', '종목명': '삼성전자', '종목코드': '005930', '섹터명': '고점형', '현재가': 55000}]
        self.alarm_data = []

        # 실시간 주가 정보를 얻어오는 리스트
        self.real_code_list = []
        self.real_data = {}
        self.real_data2 = {}
        self.sector_setting = []
        self.rg_code = []
        self.data = {}
        self.vi_test = {}
        self.buy_signal = []
        self.sell_signal = []
        self.real_exit = []


        # 증폭값
        self.v1 = 0
        self.balance = []
        self.org_depo = 0

        ### 초기 테이블 위젯 셋팅
        self.tw1_columns = ["현재 시간", "원금", "투자 중인 금액", "평가 손익", "평가 손익률", "실현손익", "수익률"]
        self.tw1.setColumnCount(len(self.tw1_columns))
        self.tw1.setHorizontalHeaderLabels(self.tw1_columns)
        for i in range(len(self.tw1_columns)):
            self.tw1.setColumnWidth(i, 125)
        self.tw1.setRowCount(1)

        self.tw2_columns = ["섹터명", "투자 금액", "수익 금액", "섹터 수익률"]
        self.tw2.setColumnCount(len(self.tw2_columns))
        self.tw2.setHorizontalHeaderLabels(self.tw2_columns)
        for i in range(len(self.tw2_columns)):
            self.tw2.setColumnWidth(i, 130)

        self.tw3_columns = ["시간", "거래상태", "매매가격", "주식수", "총금액", "섹터명", "종목명", "매수옵션", "수익률", "수익금액", "매도옵션"]
        self.tw3.setColumnCount(len(self.tw3_columns))
        self.tw3.setHorizontalHeaderLabels(self.tw3_columns)
        for i in range(len(self.tw3_columns)):
            self.tw3.setColumnWidth(i, 100)


        self.login_event_loop = QEventLoop()  # 이때 QEventLoop()는 block 기능을 가지고 있다.

        ### 키움증권 로그인
        self.k = Kiwoom()
        self.set_signal_slot()
        self.signal_login_commConnect()

        self.account_number = self.account_combo.currentText()

        # 타이머 동작
        self.set_up_timer()

        # 버튼 이벤트
        self.ok1_button.clicked.connect(self.ok1)
        self.setting_button.clicked.connect(self.open_sector_setting)
        self.start_button.clicked.connect(self.start_trading)
        self.view_down_button.clicked.connect(self.view_download)


    def setUI(self):
        self.setupUi(self)  # UI 초기값 셋업

    def set_signal_slot(self):
        self.k.kiwoom.OnEventConnect.connect(self.login_slot)

    def signal_login_commConnect(self):
        self.k.kiwoom.dynamicCall("CommConnect()")
        self.login_event_loop.exec_()

    def login_slot(self, errCode):
        if errCode == 0:
            print("로그인 성공")
            self.statusbar.showMessage("로그인 성공")
            self.get_account_info()  # 로그인시 계좌정보 가져오기
        elif errCode == 100:
            print("사용자 정보교환 실패")
        elif errCode == 101:
            print("서버접속 실패")
        elif errCode == 102:
            print("버전처리 실패")
        self.login_event_loop.exit()  # 로그인이 완료되면 로그인 창을 닫는다.

    def get_account_info(self):
        account_list = self.k.kiwoom.dynamicCall("GetLoginInfo(String)", "ACCNO")
        for n in account_list.split(';')[:-1]:
            self.account_combo.addItem(n)


    def set_up_timer(self):
        print("*** 타이머 작동")
        h1 = st1(self)
        h1.start()

        print('*** 실시간 수집 연결')
        Real(self)
        print('*** 텔레그램 연결')
        h3 = st3(self)
        h3.start()
        Vi(self)
        Logic(self)


    def start_trading(self):
        # 계좌번호 등록
        self.account_number = self.account_combo.currentText()
        print('매매 실행')
        self.start_button.setEnabled(False)
        self.flag = True
        self.label_3.setText('매매 실행 중')
        h = st(self)
        h.start()


    def ok1(self):
        self.v1 = self.v1_dsp.value()
        QMessageBox.information(self, "알림", f"증폭값: {self.v1} 등록 되었습니다.")

    def open_sector_setting(self):
        dialog = SectorSettingDialog(self, self.sector_setting)
        if dialog.exec_():
            self.sector_setting = dialog.get_settings()

    def view_download(self):
        print("trade view 다운로드 실행")
        rows = self.tw3.rowCount()
        cols = self.tw3.columnCount()
        data = []

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.tw3.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        headers = [self.tw3.horizontalHeaderItem(i).text() for i in range(cols)]
        df = pd.DataFrame(data, columns=headers)
        t = datetime.today().strftime('%y%m%d_%H%M')
        df.to_csv(f'trade_view_{t}.csv', encoding='cp949', index=False)

if __name__=='__main__':
    app = QApplication(sys.argv)
    rev = Gui()
    rev.show()
    app.exec_()
