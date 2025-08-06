from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5Singleton import Singleton

class Kiwoom(QWidget, metaclass=Singleton):

    def __init__(self, parent=None, **kwargs):
        print("로그인 시도 중 ...")
        super().__init__(parent, **kwargs)
        self.kiwoom = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')

