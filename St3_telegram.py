from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from telethon import TelegramClient, events
from datetime import timezone, timedelta, datetime
import asyncio

class st3(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        if self.parent.test:
            self.api_id = 27305613
            self.api_hash = '91f5b2b55aceb68cd9d5e842bdbd703f'
            self.session_name = 'my_session'
        else:
            self.api_id = 21951419
            self.api_hash = '4515eb81f3c466180947f72a0d3c7f46'
            self.session_name = 'my_session2'


    def run(self):
        # run() 내부에서 전체 동작을 처리하도록 구성
        # self.get_pre_mes()

        # asyncio 루프 생성 및 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.get_real_mes())
        loop.run_forever()

    def get_pre_mes(self):
        print("금일 과거 메시지를 수집합니다.")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def fetch_messages():
                async with TelegramClient(self.session_name, self.api_id, self.api_hash) as client:
                    target = await client.get_entity("@qwerreeqBot")

                    KST = timezone(timedelta(hours=9))
                    today = datetime.today().strftime("%Y%m%d")

                    async for message in client.iter_messages(target, limit=100):
                        if message.text:
                            local_time = message.date.astimezone(KST).strftime('%Y%m%d_%H%M%S')
                            if local_time.split('_')[0] == today:
                                try:
                                    sector = message.text.split('-')[0].strip()
                                    name = message.text.split('-')[1].strip()
                                    code = message.text.split('-')[-2].strip()
                                    hjg = message.text.split('-')[-1].strip()
                                    self.parent.alarm_data.append({
                                        '시간': local_time.split('_')[1],
                                        '종목명': name,
                                        '종목코드': code,
                                        '섹터명': sector,
                                        '현재가': int(float(hjg)),
                                        '체크': 'O'
                                    })
                                except Exception:
                                    pass

            loop.run_until_complete(fetch_messages())
            print(self.parent.alarm_data)

        except Exception as e:
            print('get_pre_mes ERROR (st3):', e)

    async def get_real_mes(self):
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start()
        print(" *** 실시간 메시지 수신 시작")

        @self.client.on(events.NewMessage)
        async def handler(event):
            msg = event.raw_text
            try:
                if msg:
                    sector = msg.split('-')[0].strip()
                    if sector in ["저점거래", "저점연속", "저점반등", "저점자유"]:
                        sector = "저점상승"
                    name = msg.split('-')[1].strip()
                    code = msg.split('-')[-3].strip()
                    hjg = msg.split('-')[-2].strip()
                    vol = msg.split('-')[-1].strip()
                    KST = timezone(timedelta(hours=9))
                    local_time = event.message.date.astimezone(KST).strftime('%H%M%S')

                    if ((not any(item['종목명'] == name for item in self.parent.alarm_data)) and
                        (sector in ["고점형", "저점형", "중점형", "연속상승", "거래상승", "자유상승", "순위상승", "전환상승", "반등상승", "저점상승"])):
                        print("! 신규 알림 발생 !")

                        alarm = {
                            '시간': local_time,
                            '종목명': name,
                            '종목코드': code,
                            '섹터명': sector,
                            '현재가': int(float(hjg)),
                            '거래량': int(float(vol)),
                            '체크': 'X',
                            '자산할당': '',
                            '매수전략': '',
                            '매수시각': '',
                            '매수가': '',
                            '매수수량': '',
                            '매도시각': '',
                            '매도전략': '',
                            '매도번호': '',
                            'ma5': '',
                            'ma5_1': '',
                            '분할매수': 'X',
                            '매수대기': '',
                            '재매수횟수':0,
                            'S08': False,
                            '화면번호': '',
                            '상한가가격': 0,
                            '분봉데이터': '',
                            '1차매수가':9999999,
                            'S12': True,
                            'S13': True
                        }


                        self.parent.alarm_data.insert(0, alarm)
                        print(alarm)
            except Exception as e:
                pass

