from PyQt5.QtCore import *  # 쓰레드 함수를 불러온다.
from kiwoom import *
import pandas as pd
from datetime import datetime, timedelta
import math
import requests
from kiwoomType import *
from etc import *

# Main Logic이 실행되는 스레드
class st(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.k = Kiwoom()
        self.k.kiwoom.OnReceiveTrData.connect(self.trdata_slot)
        self.k.kiwoom.OnReceiveRealData.connect(self.realdata_slot)
        self.k.kiwoom.OnReceiveMsg.connect(self._on_receive_msg)
        self.k.kiwoom.OnReceiveChejanData.connect(self._on_chejan_slot)

        self.tr_event_loop = None
        self.stop_5 = True

        self.flag_2s = True
        self.sector_view = {}
        self.recent_cg = []

        self.asset = 0
        if self.parent.test:
            self.token = '7920348394:AAEeybvzlHzM1QYUTrCa8BOJxgMskbXwzLU'
            self.chat_id = '7236384299'
        else:
            self.token = '8120794273:AAFkSmSmBzxf8qHqOkki6z9aDIq5tfU4PwY'
            self.chat_id = '-4873190652'

        #######
        self.realType = RealType()

        self.k.kiwoom.dynamicCall("SetRealRemove(QString, QString)", ["ALL", "ALL"])

        self.screen_num = 5000

        #######

        # 원금 메인 view에 등록
        self.parent.org_depo = self.get_total_depo()
        print(self.parent.org_depo)
        self.parent.tw1.setItem(0, 1, QTableWidgetItem(format(self.parent.org_depo, ',') + '원'))
        self.tw1_info()


        self.today = datetime.today().strftime("%Y%m%d")

        self.hm_list = []

        '''for code in ['005930', '396270', '196300']:
            df = self.get_min_chart(code)
            df.to_csv(f'{code}.csv', encoding='cp949', index=False)'''




        self.runs()

    def runs(self):
        while True:
            try:
                # min_data = self.get_min_chart('005930')
                # min_data.to_csv('005930.csv', encoding='cp949', index=False)



                hm = datetime.today().strftime('%H%M')
                if (hm not in self.hm_list) and (hm[-1:]=='0'):
                    self.hm_list.append(hm)
                    self.tw1_info()

                self.wait(1)

                item = self.parent.tw1.item(0, 6)
                if item is not None:
                    rate_str = item.text().replace('%', '')
                    rate_float = float(rate_str)
                    if rate_float <= -5 and self.stop_5:
                        self.stop_5 = False
                        self.msg_pop("알림", "실현 손익 -5% 초과로 인해 매매를 일시 중단합니다.")
                        continue

                self.update_tw2()

                check_alarm_list = [d for d in self.parent.alarm_data if d.get('체크') == 'X']
                if check_alarm_list:
                    print('알림 체크 리스트:', check_alarm_list)

                for info in check_alarm_list:
                    info['체크'] = 'O'
                    print('알림 발생:', info)
                    sec_time = info['시간'][:-2]
                    name = info['종목명']
                    code = str(info['종목코드']).zfill(6)
                    sector = info['섹터명']

                    # 1. 발생한 알림이 섹터 설정 조건에 부합하는지 체크 (섹터명, 매매 시간, 부정장 여부 총 3가지 체크)
                    print('섹터 설정 조건 만족 여부를 체크합니다.')
                    bjj = self.parent.bjj_checkbox.isChecked()
                    for setting in self.parent.sector_setting:
                        print(setting['섹터명'], sector, int(setting['시작시간']), int(sec_time), int(setting['종료시간']), setting['부정장'], bjj)
                        if (setting['섹터명'] == sector and int(setting['시작시간']) <= int(sec_time) <= int(setting['종료시간'])
                                and setting['부정장'] == bjj):
                            print('다음 섹터 설정 조건에 만족합니다. :', setting)
                            info['자산할당'] = int(setting['자산할당'])
                            info['매수전략'] = setting['매수전략']
                            info['매도전략'] = setting['매도전략']
                            break


                    if not info['매수전략']:
                        print('섹터 조건 미충족으로 해당 알림은 매매에서 제외합니다.')
                        self.parent.alarm_data.remove(info)
                        continue


                    # 2. 해당 종목을 보유 중인지 체크
                    print('현재 잔고:', self.parent.balance)
                    if any(bal.get('종목명') == name for bal in self.parent.balance):
                        self.parent.alarm_data.remove(info)
                        print(f"{name} : 이미 보유 중인 종목이므로 매매에서 제외합니다.")
                        continue


                    min_data = self.get_min_chart(code)

                    info['분봉데이터'] = min_data
                    yc = min_data[min_data['시간'] < int(self.today+'000000')]['종가'].iloc[0]
                    info['상한가가격'] = self.get_shg(yc)


                    self.parent.rg_code.append(code)
                    self.parent.real_data[code] = []
                    self.parent.real_data2[code] = []
                    self.parent.vi_test[code] = {}
                    fids = self.realType.REALTYPE['주식체결']['체결시간']  # 주식체결에 대한 모든 데이터를 로드할 수 있다.
                    self.k.kiwoom.dynamicCall("SetRealReg(QString, QString, QString, QString)", str(self.screen_num), code, fids, "1")
                    next(item for item in self.parent.alarm_data if item['종목코드'] == code)['화면번호'] = self.screen_num
                    self.screen_num += 1
                    print(f'{name} : 매수 1초 로직을 실행합니다.')
                    if info['매수전략'] == '기본매수':
                        info['매수대기'] = datetime.today().strftime('%H%M%S')

                    # self.wait(10)
                    # self.ms1(info)

                    '''                    
                    if info['매수전략'] == '기본매수':
                        if not (int(info['시간']) > 90600):
                            print(f'{name} : 2초 로직을 실행합니다.')
                            info['매수대기'] = datetime.today().strftime('%H%M%S')'''




            except Exception as e:
                print('알림 데이터 체크 중(st3) ERROR:', e)



            '''try:
                # S08로 매도된 종목 재매수 여부 체크
                check_list = [d for d in self.parent.alarm_data if (d.get('매도번호')=='S08') and (d.get('매수대기')=='') and (d.get('매수시각')=='')]

                for info in check_list:
                    code = info['종목코드']
                    name = info['종목명']
                    if self.diff_from_now(int(info['매도시각'])) <= 60*10 and info['재매수횟수']<2:
                        df_min = info['분봉데이터']
                        df_min = df_min.iloc[1:]
                        ma5 = int(df_min['종가'].iloc[:5].mean())
                        ma20 = int(df_min['종가'].iloc[:20].mean())
                        ma60 = int(df_min['종가'].iloc[:60].mean())
                        if 0.1<(abs(ma5-ma20)/ma20*100)<2.5 and 0.1<(abs(ma20-ma60)/ma60*100)<4:
                            p_5s = self.parent.real_data[info['종목코드']]
                            if len(p_5s) >= 1:
                                if int(p_5s[-1]) > info['현재가']:
                                    print("! 재매수01 조건 만족 -> 2초 로직 실행 ")
                                    self.telegram(f'<재매수01 알림> - {name}')
                                    self.parent.real_data[code] = []
                                    self.parent.real_data2[code] = []
                                    info['재매수횟수'] += 1
                                    info['매수전략'] = '재매수01'
                                    info['매수대기'] = datetime.today().strftime('%H%M%S')
                                    info['1차매수가'] = 9999999
                    else:
                        code = str(info['종목코드']).zfill(6)
                        self.k.kiwoom.dynamicCall("SetRealRemove(QString, QString)", str(info['화면번호']), code)
                        print(f'{info["종목명"]} 종목에 대한 실시간 데이터 수집을 중단합니다.')
                        del self.parent.real_data[code]
                        del self.parent.real_data2[code]
                        del self.parent.data[code]
                        del self.parent.vi_test[code]
                        self.parent.alarm_data.remove(info)
                        self.parent.rg_code.remove(code)

            except Exception as e:
                print('재매수01 로직 체크 중(st3) ERROR:', e)'''



            # S05, 6, 7, 10, 11에 대한 재매수 로직 실행
            try:
                # S05, 6, 7, 10, 11로 매도된 종목 재매수 여부 체크
                check_list = [d for d in self.parent.alarm_data if ((d.get('매도번호')=='S05') or (d.get('매도번호')=='S06')
                or (d.get('매도번호')=='S07') or (d.get('매도번호')=='S10') or (d.get('매도번호')=='S11'))
                and (d.get('매수대기')=='') and (d.get('매수시각')=='')]

                for info in check_list:
                    code = info['종목코드']
                    name = info['종목명']
                    if self.diff_from_now(int(info['매도시각'])) <= 60*60 and info['재매수횟수']<2:
                        df_min = info['분봉데이터']
                        df_min = df_min.iloc[1:]
                        ma5 = int(df_min['종가'].iloc[:5].mean())
                        ma20 = int(df_min['종가'].iloc[:20].mean())
                        ma20_1 = int(df_min['종가'].iloc[1:21].mean())
                        ma60 = int(df_min['종가'].iloc[:60].mean())
                        ma120 = int(df_min['종가'].iloc[:120].mean())
                        op = df_min['시가'].iloc[0]
                        cp = df_min['종가'].iloc[0]
                        hp = df_min['고가'].iloc[0]
                        op1 = df_min['시가'].iloc[1]
                        cp1 = df_min['종가'].iloc[1]
                        vol = df_min['거래량'].iloc[0]
                        op_ma5 = df_min['시가'].iloc[1:6].mean()
                        cp_ma5 = df_min['종가'].iloc[1:6].mean()
                        vol_ma5 = df_min['거래량'].iloc[1:6].mean()

                        ms = True
                        if (info['현재가'] < ma60 and op<cp and cp-op>(cp_ma5-op_ma5)*2 and cp-op>ma20-ma60 and ma20>ma20_1
                            and info['거래량']*0.25<vol and vol_ma5*4<vol):
                            for j in [60, 120]:
                                for i in range(5):
                                    if not (df_min['종가'].iloc[i:j+i].mean() > df_min['종가'].iloc[i+1:j+i+1].mean()):
                                        ms = False
                            ms2 = False
                            for i in range(1, 10):
                                if df_min['종가'].iloc[i:i+20].mean() < df_min['종가'].iloc[i+1:i+21].mean():
                                    ms2 = True

                            if ms and ms2:
                                print("! 재매수02 조건 만족 -> 매수 1초 로직 실행 ")
                                self.telegram(f'<재매수02 알림> - {name}')
                                self.parent.real_data[code] = []
                                self.parent.real_data2[code] = []
                                info['재매수횟수'] += 1
                                info['매수전략'] = '재매수02'
                                info['매수대기'] = datetime.today().strftime('%H%M%S')
                                info['1차매수가'] = 9999999

                    else:
                        code = str(info['종목코드']).zfill(6)
                        self.k.kiwoom.dynamicCall("SetRealRemove(QString, QString)", str(info['화면번호']), code)
                        print(f'{info["종목명"]} 종목에 대한 실시간 데이터 수집을 중단합니다.')
                        del self.parent.real_data[code]
                        del self.parent.real_data2[code]
                        del self.parent.data[code]
                        del self.parent.vi_test[code]
                        self.parent.alarm_data.remove(info)
                        self.parent.rg_code.remove(code)

            except Exception as e:
                print('재매수02 로직 체크 중(st3) ERROR:', e)




            try:
                # 매수대기 값이 빈 값이 아닌 경우
                check_list = [d for d in self.parent.alarm_data if d.get('매수대기')]
                if check_list:
                    print("1초 로직 체크 리스트 (매수) : ", [chk['종목명'] for chk in check_list])
                    check_code_list = [chk['종목코드'] for chk in check_list]

                    del_list = []
                    prt_real_data = self.parent.real_data.copy()
                    for code in prt_real_data.keys():
                        if code not in check_code_list:
                            del_list.append(code)

                    for code in del_list:
                        del prt_real_data[code]

                    # print(prt_real_data)

                for info in check_list:
                    if info['종목코드'] not in self.parent.real_data:
                        print(f"종목코드 {info['종목코드']} 데이터 수집 등록 전입니다.")
                        continue

                    if self.diff_from_now(int(info['시간'])) <= 60*30:
                        p_5s = self.parent.real_data[info['종목코드']]

                        '''
                        # 시각: 실시간 데이터를 저장
                        t2 = datetime.today().strftime('%H%M%S')
                        self.parent.vi_test[info['종목코드']][int(t2)] = p_5s.copy()
    
                        # 1분전 시각
                        t3 = (datetime.today() - timedelta(minutes=1)).strftime('%H%M%S')
    
                        # 실시간 데이터
                        vi = self.parent.vi_test[info['종목코드']]
    
                        # 1분전 시각 이후의 데이터만 남김
                        vi_60 = {k: v for k, v in vi.items() if k >= int(t3)}
    
                        # 1분 동안의 데이터 저장
                        self.parent.vi_test[info['종목코드']] = vi_60
    
                        # 값이 50개 이상 & 모든 value가 동일한지 비교
                        if len(vi_60) >= 25 and int(t2) >= 91100:
                            if all(v == list(vi_60.values())[0] for v in vi_60.values()):
                                print(f"종목코드 {info['종목코드']} vi 판단 --> 로직에서 제외")
                                info['매수대기'] = ''
                        '''


                        # 알림 분봉의 거래량(기준)
                        if info['섹터명'] == "저점상승":
                            vol_r = 2
                        else:
                            vol_r = 1

                        al_time = self.today + info['시간'][:4] + '00'
                        df = info['분봉데이터']
                        al_vol = df[df['시간'] < int(al_time)]['거래량'].iloc[0]
                        al_cp = df[df['시간'] < int(al_time)]['종가'].iloc[0]

                        real_cp = df['종가'].iloc[0]
                        real_op = df['시가'].iloc[0]
                        real_vol = df['거래량'].iloc[0]
                        try:
                            real_r = df['등락률'].iloc[0]
                        except:
                            continue
                        print(f" ******* 매수 로직 체크 - 종목명: {info['종목명']}")
                        print(f"실시간 거래량:{real_vol} 알림 거래량: {al_vol} / 실시간 현재가: {real_cp} 실시간 시가: {real_op} 알림 종가: {al_cp} / 등락률: {real_r}")

                        # 조건 1~4
                        if real_vol >= al_vol*vol_r and real_cp > real_op and real_cp > al_cp and 2 <= real_r < 12 and len(p_5s) == 3:
                            # 생성 완료된 분봉에 대한 이평값 계산
                            ma5 = int(df['종가'].iloc[1:6].mean())
                            ma20 = int(df['종가'].iloc[1:21].mean())
                            ma60 = int(df['종가'].iloc[1:61].mean())
                            ma120 = int(df['종가'].iloc[1:121].mean())
                            print(f"ma5:{ma5} / ma20:{ma20} / ma60:{ma60} / ma120:{ma120}")
                            ma = sorted([ma5, ma20, ma60, ma120])

                            # 조건 5~7
                            if (abs(ma[-1]-ma[0])/ma[0]*100)<6 and (abs(ma[-1]-ma[-2])/ma[-2]*100)<3 and real_op>al_cp*0.994:
                                df1 = df[df['거래량'] != 0]
                                df2 = df1[df1['시간'] > int(self.today+'000000')].iloc[1:6]

                                # 조건 8
                                print(f'최근 5분봉 종-시 평균값: {(df2["종가"] - df2["시가"]).abs().mean()}')
                                if real_cp-real_op > (df2['종가'] - df2['시가']).abs().mean():

                                    print(f"종목코드 {info['종목코드']} / 2초 전 가격: {p_5s[-3]} 1초 전 가격: {p_5s[-2]} 현재 가격: {p_5s[-1]}")
                                    if int(p_5s[-3]) <= int(p_5s[-2]) < int(p_5s[-1]):
                                        print("! 1초 로직 조건 만족 -> 매수 로직 실행 !")
                                        info['매수대기'] = ''
                                        self.basic_ms(info)

                    else:
                        code = str(info['종목코드']).zfill(6)
                        self.k.kiwoom.dynamicCall("SetRealRemove(QString, QString)", str(info['화면번호']), code)
                        print(f'{info["종목명"]} 종목에 대한 실시간 데이터 수집을 중단합니다.')
                        del self.parent.real_data[code]
                        del self.parent.real_data2[code]
                        del self.parent.data[code]
                        del self.parent.vi_test[code]
                        self.parent.alarm_data.remove(info)
                        self.parent.rg_code.remove(code)
                        info['매수대기'] = ''

            except Exception as e:
                print('1초 로직 체크 중(st3) ERROR:', e)



            try:
                # 매수 전략이 탄력매수 & 매수시각이 빈 값(매수 X)
                check_list = [d for d in self.parent.alarm_data if (d.get('매수전략') == '탄력매수') and (d.get('매수시각') == '') and (d.get('매수대기') == '')]
                for info in check_list:
                    if self.diff_from_now(int(info['시간'])) <= 60*10:
                        name = info['종목명']
                        code = info['종목코드']
                        df_min = info['분봉데이터']
                        df_min = df_min.iloc[1:]
                        op = df_min['시가'].iloc[0]
                        cp = df_min['종가'].iloc[0]
                        op_1 = df_min['시가'].iloc[1]
                        cp_1 = df_min['종가'].iloc[1]
                        op_2 = df_min['시가'].iloc[2]
                        cp_2 = df_min['종가'].iloc[2]
                        op_3 = df_min['시가'].iloc[3]
                        cp_3 = df_min['종가'].iloc[3]
                        ma5 = int(df_min['종가'].iloc[:5].mean())
                        ma5_1 = int(df_min['종가'].iloc[1:6].mean())
                        ma20 = int(df_min['종가'].iloc[:20].mean())
                        ma20_1 = int(df_min['종가'].iloc[1:21].mean())
                        ma60 = int(df_min['종가'].iloc[:60].mean())
                        ma60_1 = int(df_min['종가'].iloc[1:61].mean())
                        ma120 = int(df_min['종가'].iloc[:120].mean())
                        ma120_1 = int(df_min['종가'].iloc[1:121].mean())
                        print('조건 만족 여부 체크')

                        if ((ma20>=ma20_1) and (ma60>=ma60_1) and (ma120>=ma120_1)
                            and (op<cp) and ((op_1>cp_1) or (op_2>cp_2) or (op_3>cp_3))
                            and (cp>ma20) and (cp>ma60) and (cp>ma120)):
                            print(f'{name} : 탄력 매수 조건 만족 / 매수 1초 로직을 실행합니다.')

                            self.parent.real_data[code] = []
                            self.parent.real_data2[code] = []
                            info['매수대기'] = datetime.today().strftime('%H%M%S')


            except Exception as e:
                print('탄력 매수 체크 중(st3) ERROR:', e)

            # 추적매수
            '''try:
                # 매수시각이 빈 값(매수 X) & 매수 대기 상태 X 모든 종목 추적
                check_list = [d for d in self.parent.alarm_data if (d.get('매수시각') == '') and (d.get('매수대기') == '') and (d.get('매도시각') == '')]
                for info in check_list:
                    if self.diff_from_now(int(info['시간'])) <= 60*6:
                        pass

                    elif 60*6 < self.diff_from_now(int(info['시간'])) <= 60*60:
                        name = info['종목명']
                        code = info['종목코드']
                        df_min = info['분봉데이터']
                        df_min = df_min.iloc[1:]
                        op = df_min['시가'].iloc[0]
                        cp = df_min['종가'].iloc[0]
                        cp_1 = df_min['종가'].iloc[1]
                        cp_2 = df_min['종가'].iloc[2]
                        cp_3 = df_min['종가'].iloc[3]
                        cp_4 = df_min['종가'].iloc[4]
                        cp_5 = df_min['종가'].iloc[5]

                        ma5 = int(df_min['종가'].iloc[:5].mean())
                        ma20 = int(df_min['종가'].iloc[:20].mean())
                        ma60 = int(df_min['종가'].iloc[:60].mean())
                        ma120 = int(df_min['종가'].iloc[:120].mean())
                        vol = df_min['거래량'].iloc[0]
                        vol_1 = df_min['거래량'].iloc[1]


                        if ((cp>info['현재가']) and (cp_1<info['현재가']) and (op<cp) and (cp*vol>100000000)
                            and (vol>vol_1) and (ma5>ma20>=ma60) and (ma5>ma20>=ma120)
                            and (0.1<(abs(ma5-ma20)/ma20*100)<2.5) and (0.1<(abs(ma20-ma60)/ma60*100)<4)
                            and (cp_2<info['현재가']) and (cp_3<info['현재가']) and (cp_4<info['현재가']) and (cp_5<info['현재가'])):

                            ms = True
                            for j in [20, 60, 120]:
                                for i in range(4):
                                    if not (df_min['종가'].iloc[i:j+i].mean() >= df_min['종가'].iloc[i+1:j+i+1].mean()):
                                        ms = False
                                        break

                            if ms:
                                print(f'{name} : 추적 매수 조건 만족 / 2초 로직을 실행합니다.')
                                self.telegram(f'<추적 매수 알림> - {name}')
                                self.parent.real_data[code] = []
                                self.parent.real_dat2[code] = []
                                info['매수대기'] = datetime.today().strftime('%H%M%S')

                    else:
                        code = str(info['종목코드']).zfill(6)
                        self.k.kiwoom.dynamicCall("SetRealRemove(QString, QString)", str(info['화면번호']), code)
                        print(f'{info["종목명"]} 종목에 대한 실시간 데이터 수집을 중단합니다.')
                        del self.parent.real_data[code]
                        del self.parent.real_data2[code]
                        del self.parent.data[code]
                        del self.parent.vi_test[code]
                        self.parent.rg_code.remove(code)
                        self.parent.alarm_data.remove(info)

            except Exception as e:
                print('추적 매수 체크 중(st3) ERROR:', e)
            '''


            try:
                for bal in self.parent.balance:

                    name = bal['종목명']
                    print(f" ******* 매도 로직 체크 - 종목명: {name}")

                    try:
                        info = next((d for d in self.parent.alarm_data if d['종목명'] == name))
                    except:
                        continue

                    code = info['종목코드']
                    ms_st = info['매수전략']
                    md_st = info['매도전략']

                    df = info['분봉데이터']
                    hjg = df['종가'].iloc[0]
                    df_min = df.iloc[1:]

                    cp = df_min['종가'].iloc[0]
                    ma5 = int(df_min['종가'].iloc[:5].mean())
                    ma5_1 = int(df_min['종가'].iloc[1:6].mean())
                    ma5_2 = int(df_min['종가'].iloc[2:7].mean())
                    ma5_3 = int(df_min['종가'].iloc[3:8].mean())
                    ma20 = int(df_min['종가'].iloc[:20].mean())
                    ma20_1 = int(df_min['종가'].iloc[1:21].mean())
                    ma20_2 = int(df_min['종가'].iloc[2:22].mean())
                    ma20_3 = int(df_min['종가'].iloc[3:23].mean())
                    ma60 = int(df_min['종가'].iloc[:60].mean())
                    ma120 = int(df_min['종가'].iloc[:120].mean())


                    if md_st == '트레일링스탑':
                        ms_time = int(datetime.today().strftime('%Y%m%d') + str(info['매수시각']))
                        # print(f"{name} 종목에 대한 트레일링 스탑 매도 로직 실행")
                        ave_amp = (df_min["고가"][:14] - df_min["저가"][:14]).mean()
                        hr = df_min[df_min['시간'] > int(ms_time)]['고가'].max()
                        # print(f"현재가 : {hjg} / 고점: {hr} / 평균 진폭: {ave_amp} / 진폭값: {self.parent.v1}\n")
                        if hjg < hr - (ave_amp * float(self.parent.v1)):
                            print(f"트레일링 스탑 매도 조건 만족(S05) : {name}")
                            self.sell(info, 'S05')
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            continue

                    elif md_st == '5전환매도':
                        # print(f"{name} 종목에 대한 5이평값 전환 매도 로직 실행")
                        if (ma5 < ma5_1) and (ma5_1 > ma5_2) and (ma5_2 > ma5_3):
                            print(f"이평가하락 매도 조건 만족(S06) : {name}")
                            self.sell(info, 'S06')
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            continue

                    elif md_st == '20전환매도':
                        # print(f"{name} 종목에 대한 20이평값 전환 매도 로직 실행")
                        # if (ma20<ma20_1) or ((ma20==ma20_1) and (ma20_1>ma20_2) and (ma20_2>ma20_3)):
                        if ma20<ma20_1:
                            print(f"이평가하락 매도 조건 만족(S07) : {name}")
                            self.sell(info, 'S07')
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            continue

                    elif md_st == '교차매도':
                        # print(f"{name} 종목에 대한 교차 매도 로직 실행")
                        if (ma5 <= ma20) and (ma5 > info['현재가']):
                            print(f"교차매도 조건 만족(S10) : {name}")
                            self.sell(info, 'S10')
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            continue

                    elif md_st == '복합매도':
                        ma = [ma5, ma20, ma60, ma120]
                        ma.sort()
                        if (info['현재가'] < ma60 and ma[3]-ma[2]>=ma[2]-ma[0] and (abs(ma[2]-ma[0])/ma[0]*100)>3.5) or (info['현재가'] < ma120):
                            print(f"복합 매도 조건 만족(S11) : {name}")
                            self.sell(info, 'S11')
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            continue

                    elif md_st == '스네이크셀':
                        # print('------- 스네이크셀 -------')
                        if info['현재가'] < ma120:
                            print(f"스네이크셀 매도 조건 만족(S15) : {name}")
                            print(f"알림 분봉 종가: {info['현재가']} / 120이평값: {ma120}")
                            self.sell(info, 'S15')
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            continue

                        vol_sum = 0
                        ms_time = self.today + info['매수시각'][:4] + '00'

                        df = info['분봉데이터'].iloc[1:]
                        df = df[df['거래량'] != 0]
                        df1 = df[df['시간'] >= int(ms_time)]
                        df2 = df[df['시간'] > int(self.today + '000000')]

                        if len(df1) >= 3:
                            for i in range(len(df1)):
                                t = df1['시간'].iloc[i]
                                vol_10 = df2[df2['시간']<=int(t)]['거래량'].iloc[:10].mean()
                                vol = df2[df2['시간']<=int(t)]['거래량'].iloc[0]
                                op = df2[df2['시간']<=int(t)]['시가'].iloc[0]
                                cp = df2[df2['시간']<=int(t)]['종가'].iloc[0]
                                # print(f"{t}분봉 - 시가: {op} / 종가: {cp} / 거래량: {vol} / 10분평균거래량: {vol_10}")

                                if vol >= vol_10:
                                    if cp >= op:
                                        vol_sum += vol-vol_10
                                        # print(f"+{vol-vol_10}")
                                else:
                                    vol_sum -= abs(vol-vol_10)
                                    # print(f"-{abs(vol-vol_10)}")


                            if vol_sum < 0:
                                print(f"스네이크셀 매도 조건 만족(S15) : {name}")
                                print(f'계산의 총합: {vol_sum}')
                                self.sell(info, 'S15')
                                info['매수시각'] = ''
                                info['매수대기'] = ''
                                continue



                    # 비상 탈출 매도 (공통 적용)
                    if int(datetime.today().strftime('%H%M%S')) > 151000 or (info['상한가가격'] == hjg):
                        print(f'비상탈출 매도 S03 : {name}')
                        self.sell(info, 'S03')
                        info['매수시각'] = ''
                        info['매수대기'] = ''
                        continue

                    if 60*10 <= self.diff_from_now(info['매수시각']):
                        try:
                            if info['1차매수가'] > cp:
                                p_5s = self.parent.real_data[code]
                                if len(p_5s) >= 3:
                                    if info['매수전략'] == '재매수01' or info['매수전략'] == '재매수02':
                                        cp = info['1차매수가']
                                    else:
                                        cp = info['현재가']

                                    print(f"[매도 1초 로직 S09] 종목코드 {info['종목코드']} / 2초 전 가격: {p_5s[-3]} 1초 전 가격: {p_5s[-2]} 현재 가격: {p_5s[-1]}")
                                    if (cp > int(p_5s[-3])) and (cp > int(p_5s[-2])) and (cp > int(p_5s[-1])) and (int(p_5s[-3]) > int(p_5s[-2]) > int(p_5s[-1])):
                                        print(f'비상탈출 매도 S09 : {name}')
                                        info['매도번호'] = 'S09'
                                        info['매수시각'] = ''
                                        info['매수대기'] = ''
                                        self.sell(info, 'S09')
                                        continue
                        except:
                            pass

                    if self.diff_from_now(info['매수시각']) <= 60*10:
                        try:
                            p_5s = self.parent.real_data[code]
                            if len(p_5s) >= 3:
                                cp = info['현재가']

                                if cp > int(p_5s[-1]):
                                    print(f"[매도 1초 로직 S08] 종목코드 {info['종목코드']} / 2초 전 가격: {p_5s[-3]} 1초 전 가격: {p_5s[-2]} 현재 가격: {p_5s[-1]}")

                                if (cp > int(p_5s[-3])) and (cp > int(p_5s[-2])) and (cp > int(p_5s[-1])) and (int(p_5s[-3]) > int(p_5s[-2]) > int(p_5s[-1])):
                                    print(f'비상탈출 매도 S08 : {name}')
                                    info['매도번호'] = 'S08'
                                    info['매수시각'] = ''
                                    info['매수대기'] = ''
                                    self.sell(info, 'S08')
                                    continue
                        except:
                            pass


                    '''
                    # S12
                    if info['S12']:
                        if info['매수시각'][2:4] == info['시간'][2:4]:
                            # vi 데이터 제거를 위해 거래량이 0인 행 제거
                            df = df[df['거래량'] != 0]
                            # 매수시각 이후 데이터
                            check_df = df[df['시간'] > int(self.today+info['매수시각'][:4]+'00')]

                            # 옵션 A를 만족한 적이 없고 매수 시각 이후 데이터가 1개인 경우
                            if len(check_df) == 1 and (info['S12']!='A'):
                                p_5s = self.parent.real_data2[code]

                                print(f"종목코드 {info['종목코드']} / 2분 후 분봉 시가: {check_df['시가'].iloc[0]} / 4초 전 가격: {p_5s[-3]} 2초 전 가격: {p_5s[-2]} 현재 가격: {p_5s[-1]}")
                                if int(check_df['시가'].iloc[0]) > int(p_5s[-1]) and (int(p_5s[-3]) > int(p_5s[-2]) > int(p_5s[-1])):
                                    amount = math.ceil(int(bal['보유수량'])/2)
                                    self.sell(info, 'S12', amount)
                                    info['S12'] = 'A'

                            if len(check_df) == 2:
                                print(f"종목코드 {info['종목코드']} / 2분 후 분봉 시가: {check_df['시가'].iloc[0]} 2분 후 분봉 종가: {check_df['종가'].iloc[1]}")
                                if int(check_df['시가'].iloc[1]) > int(check_df['종가'].iloc[1]):
                                    amount = math.ceil(int(bal['보유수량']) / 2)
                                    self.sell(info, 'S12', amount)
                                    info['S12'] = False
                                else:
                                    info['S12'] = False
                        else:
                            info['S12'] = False
                    '''

                    # S13
                    try:
                        if info['S13']:
                            # print("------- S13 -------")
                            p_5s = self.parent.real_data[code]

                            # 알림 분봉의 거래량(기준)
                            al_time = self.today + info['시간'][:4] + '00'
                            df = info['분봉데이터']
                            df = df[df['거래량'] != 0]

                            al_vol = df[df['시간'] < int(al_time)]['거래량'].iloc[0]

                            real_cp = df['종가'].iloc[0]
                            real_op = df['시가'].iloc[0]
                            real_vol = df['거래량'].iloc[0]

                            df1 = df[df['시간'] >= int(al_time)]
                            if len(df1) > 5:
                                print("알림 발생 5분봉 초과로 인한 S13 로직 적용 중단")
                                info['S13'] = False
                                continue

                            # S13 조건 1, 2
                            if real_vol >= al_vol and real_cp < real_op:

                                df2 = df[df['시간'] > int(self.today+'000000')].iloc[1:11]

                                # 조건 4
                                if real_op - real_cp > (df2['종가'] - df2['시가']).abs().mean() and len(p_5s) == 3:
                                    print(f"실시간 거래량: {real_vol} 알림 거래량: {al_vol} / 실시간 현재가: {real_cp} 실시간 분봉 시가: {real_op}")
                                    print(f'최근 10분봉 종-시 평균값: {(df2["종가"] - df2["시가"]).abs().mean()}')
                                    print(f"[매도 1초 로직 S13] 종목코드 {info['종목코드']} / 2초 전 가격: {p_5s[-3]} 1초 전 가격: {p_5s[-2]} 현재 가격: {p_5s[-1]}")
                                    if int(p_5s[-3]) > int(p_5s[-2]) > int(p_5s[-1]):
                                        print(f'비상탈출 매도 S13 : {name}')
                                        info['매도번호'] = 'S13'
                                        info['매수시각'] = ''
                                        info['매수대기'] = ''
                                        self.sell(info, 'S13')
                                        continue

                    except Exception as e:
                        print(e)


                    # S14
                    try:
                        # print("------- S14 -------")
                        df = info['분봉데이터']
                        df = df[df['거래량'] != 0]
                        df1 = df[df['시간'] > int(self.today + '000000')].iloc[2:7]
                        df2 = df[df['시간'] > int(self.today + '000000')].iloc[1:11]
                        df3 = df[df['시간'] > int(self.today + '000000')].iloc[1:6]

                        cp = df['종가'].iloc[1]
                        op = df['시가'].iloc[1]
                        vol = df['거래량'].iloc[1]


                        if ((op-cp > (df1['종가']-df1['시가']).abs().mean()) and (op>cp)
                            and ((vol>df2['거래량'].mean()) or (vol>df3['거래량'].mean()))):
                            print(f'비상탈출 매도 S14 : {name}')
                            print(f'현재시점 - 시가: {op} / 종가: {cp} / 거래량: {vol}')
                            print(f'1분전 시점 5분봉 종-시 평균값: {(df1["종가"] - df1["시가"]).abs().mean()}')
                            print(f"현재시점 10분 평균 거래량: {df2['거래량'].mean()} / 5분 평균 거래량: {df3['거래량'].mean()}")

                            info['매도번호'] = 'S14'
                            info['매수시각'] = ''
                            info['매수대기'] = ''
                            self.sell(info, 'S14')
                            continue



                    except Exception as e:
                        print(e)


            except Exception as e:
                print('매도 체크 중(st3) ERROR:', e)




    # 보유 종목이 없을 때 실행되는 ms1
    def ms1(self, info):
        try:
            print('order ms1')
            sector = info['섹터명']
            depo = self.get_deposit()
            ass = info['자산할당']
            depo_ass = int(depo * ass / 100)
            print(f"매수 가능 금액 {depo}원 / {sector}섹터의 할당 자산 {ass}% -> {depo_ass}원 매수")

            '''mar = self.get_margin_rate(info['종목코드'])
            ms_depo = int(depo_ass / mar * 100)
            print(f"매수 금액 {depo_ass}원 / 증거금률 {mar}% --> 최종 매수 금액 {ms_depo}원")
            self.asset = ms_depo'''

            self.asset = depo_ass
            self.buy(info)

        except Exception as e:
            print(f"ms1 Error: {e}")


    def ms2(self, info):
        try:
            print('order ms2')
            code = info['종목코드']
            depo = depo_org = int(self.get_deposit())
            depo1 = self.get_total_depo()
            print(f"현재 매수 가능 금액은 {depo}원, 총 평가 자산은 {depo1}원 입니다.")

            ass = info['자산할당']
            depo_ass = int(depo1 * ass / 100)

            '''mar = self.get_margin_rate(code)
            print(f"해당 종목의 매수 최대 가능 한도는 {depo_ass}원 / 증거금률은 {mar}% 입니다.")'''


            '''# 분할 로직을 위한 매도 대상 종목 및 금액 판단 / 분할에서 제외되는 종목의 금액 제외
            md_code_list = []
            for bal in self.parent.balance:
                print(f"보유 종목 {bal['종목코드']}에 대한 증거금: {self.get_margin_rate(bal['종목코드'])}")
                if self.get_margin_rate(bal['종목코드']) >= mar:
                    md_code_list.append(bal['종목코드'])
                else:
                    depo1 -= int(bal['평가금액']*self.get_margin_rate(bal['종목코드'])/100)'''


            # 분할 로직을 위한 매도 대상 종목 및 금액 판단 / 분할에서 제외되는 종목의 금액 제외
            md_code_list = [bal['종목코드'] for bal in self.parent.balance]
            print('md_code_list', md_code_list)
            split_bal = int(depo1/(len(md_code_list)+1))
            print(f"분할 대상 종목 수는 {len(md_code_list)+1}개로 각 할당 금액은 {split_bal}원 입니다.")

            # 매수 한도 금액과 분할 고려 할당된 금액 중 낮은 금액으로 매수
            if split_bal <= depo_ass:
                ms_depo = split_bal
            else:
                ms_depo = depo_ass

            # 예수금으로 매수가 가능한 경우
            if depo_org >= ms_depo:
                print(f"할당 금액 {ms_depo}원 / 매수가능금액 {depo_org}원으로 즉시 매수를 실행합니다.")

                '''ms_depo2 = int(ms_depo / mar * 100)
                print(f"매수 금액 {ms_depo}원 / 증거금률 {mar}% --> 최종 매수 금액 {ms_depo2}원")
                self.asset = ms_depo2'''

                self.asset = ms_depo
                self.buy(info)

            # 분할이 필요한 경우
            else:
                # 수익률 (+)인 종목 존재 시 분할 전략을 위한 매도 실행
                # 필요한 금액
                md_depo = ms_depo - depo_org
                print(f"할당 금액 {ms_depo}원 / 매수가능금액 {depo_org}원으로 {md_depo}원에 대한 분할 매도를 실행합니다.")

                for bal in self.parent.balance:
                    if bal['종목코드'] in md_code_list:
                        print(f'자산 분할을 위한 매도 실행')
                        try:
                            info_md = next((d for d in self.parent.alarm_data if d['종목명'] == bal['종목명']))
                            print(info_md)
                        except:
                            info_md = {'종목코드': bal['종목코드'], '섹터명': '?', '매수전략': '?'}


                        '''print(f'현재가: {bal["현재가"]} / 매도수량: {math.ceil((md_depo / len(md_code_list))/self.get_margin_rate(bal["종목코드"])*100 / bal["현재가"])} 주문 실행')
                        self.sell(info_md, 'S04', math.ceil((md_depo / len(md_code_list))/self.get_margin_rate(bal["종목코드"])*100 / bal["현재가"]))'''

                        self.sell(info_md, 'S04', math.ceil((md_depo/len(md_code_list))/bal["현재가"]))

                print(f"할당 금액 {ms_depo}원에 대한 매수를 실행합니다.")

                '''ms_depo2 = int(ms_depo / mar * 100)
                print(f"매수 금액 {ms_depo}원 / 증거금률 {mar}% --> 최종 매수 금액 {ms_depo2}원")
                self.asset = ms_depo2'''

                self.asset = ms_depo
                self.buy(info)


            '''
            # 1/N 분할 로직 실행
            # (예수금 + 보유 금액) * 자산 한도
            depo1 = int((depo + sum(bal['평가금액'] for bal in self.parent.balance)))
            print(f"현재 예수금은 {depo}원, 보유 평가 금액을 더한 총 자산은 {depo1}원 입니다.")

            ass = info['자산할당']
            depo_ass = int(depo1 * ass / 100)
            print(f"해당 종목의 매수 최대 가능 한도는 {depo_ass}원 입니다.")

            # 수익률 < 0인 종목의 평가금액은 제외 (분할에서 제외)
            depo2 = depo1 - sum(bal['평가금액'] for bal in self.parent.balance if bal['수익률'] < 0)
            print(f"수익률 < 0 인 종목을 제외한 분할 대상 금액은 {depo2}원 입니다.")

            # 분할 로직을 위한 매도 대상 종목 및 금액 판단
            ms_count = sum(1 for bal in self.parent.balance if bal['수익률'] >= 0)
            split_bal = int(depo2/(ms_count+1))

            print(f"분할 대상 종목 수는 {ms_count+1}개로 각 할당 금액은 {split_bal}원 입니다.")
            # 매수 한도 금액과 분할 고려 할당된 금액 중 낮은 금액으로 매수
            if split_bal <= depo_ass:
                ms_depo = split_bal
            else:
                ms_depo = depo_ass

            # 예수금으로 매수가 가능한 경우
            if depo > ms_depo:
                print(f"할당 금액 {ms_depo}원 / 예수금 {depo}원으로 즉시 매수를 실행합니다.")
                ms_price = self.get_hoga(code)[-2]
                self.wait(0.5)
                amount = int(ms_depo / ms_price)
                self.buy(info, amount, ms_price)

            # 분할이 필요한 경우
            else:
                # 수익률 (+)인 종목 존재 시 분할 전략을 위한 매도 실행
                # 필요한 금액
                md_depo = ms_depo-depo
                print(f"할당 금액 {ms_depo}원 / 예수금 {depo}원으로 {md_depo}원에 대한 분할 매도를 실행합니다.")

                if ms_count:
                    for bal in self.parent.balance:
                        if bal['수익률'] >= 0:
                            print(f'자산 분할을 위한 매도 실행')
                            try:
                                info_md = next((d for d in self.parent.alarm_data if d['종목명'] == bal['종목명']))
                                print(info_md)
                            except:
                                info_md = {'종목코드': bal['종목코드'], '섹터명': '?', '매수전략': '?'}

                            print(f'현재가: {bal["현재가"]} / 매도수량: {math.ceil((md_depo/ms_count)/bal["현재가"])} 주문 실행')
                            self.sell(info_md,'S04', math.ceil((md_depo/ms_count)/bal['현재가']))

                print(f"할당 금액 {ms_depo}원에 대한 매수를 실행합니다.")
                ms_price = self.get_hoga(code)[-2]
                amount = int(ms_depo / ms_price)
                self.buy(info, amount, ms_price)
                '''
        except Exception as e:
            print(f"ms2 Error: {e}")


    def ms3(self, info):
        try:
            print("매도 종목 발생으로 인한 매수 대기 종목 매수 로직 실행")
            depo = self.get_deposit()
            depo1 = self.get_total_depo()
            ass = info['자산할당']
            depo_ass = int(depo1 * ass / 100)
            print(f"현재 매수 가능 금액은 {depo}원 / 해당 섹터의 매수 한도 금액은 {depo_ass}입니다.")

            mar = self.get_margin_rate(info['종목코드'])
            if depo > depo_ass:
                ms_depo = int(depo_ass/mar*100)
                print(f"매수 금액 {depo_ass}원 / 증거금률 {mar}% --> 최종 매수 금액 {ms_depo}원")
                self.asset = ms_depo
            else:
                ms_depo = int(depo / mar * 100)
                print(f"매수 금액 {depo}원 / 증거금률 {mar}% --> 최종 매수 금액 {ms_depo}원")
                self.asset = ms_depo

            self.buy(info)

        except Exception as e:
            print('ms3 ERROR : ', e)



    def buy(self, info):
        try:
            info['매수시각'] = datetime.today().strftime('%H%M%S')
            code = info['종목코드']
            hoga5 = get_hoga(self.parent.data[code], 5)
            print(f"실시간 현재가: {self.parent.data[code]} / 매수 5호가: {hoga5}")
            amount = int(self.asset / hoga5)
            print(code, "매수주문", amount)

            self.send_order('send_buy_order', '7777', '1', code, amount, hoga5, '00')

            '''self.wait(10)
            amount = int(self.asset / info['상한가가격'])
            print(code, "매수주문2", amount)
            if amount == 0:
                print("매수 주문 가능 수량 X --> 매수 로직 종료")
                self.tw1_info()
                self.parent.real_data[code] = []
                self.parent.real_data2[code] = []
                return

            print(f"실시간 현재가 : {self.parent.data[code]} / (알림 시점)분봉 종가: {info['현재가']}")
            if self.parent.data[code] < info['현재가']:
                print("실시간 현재가 < (알림 시점)분봉 종가 --> 매수 로직 종료")
                self.tw1_info()
                self.parent.real_data[code] = []
                self.parent.real_data2[code] = []
                return

            self.send_order('send_buy_order', '7777', '1', code, amount, 0, '03')
            self.wait(10)


            amount = int(self.asset / info['상한가가격'])
            print(code, "매수주문3", amount)
            if amount == 0:
                print("매수 주문 가능 수량 X --> 매수 로직 종료")
                self.tw1_info()
                self.parent.real_data[code] = []
                self.parent.real_data2[code] = []
                return

            print(f"실시간 현재가 : {self.parent.data[code]} / (알림 시점)분봉 종가: {info['현재가']}")
            if self.parent.data[code] < info['현재가']:
                print("실시간 현재가 < (알림 시점)분봉 종가 --> 매수 로직 종료")
                self.tw1_info()
                self.parent.real_data[code] = []
                self.parent.real_data2[code] = []
                return

            self.send_order('send_buy_order', '7777', '1', code, amount, 0, '03')
            self.wait(3)'''

            self.tw1_info()
            self.parent.real_data[code] = []
            self.parent.real_data2[code] = []

        except Exception as e:
            print(f"buy Error: {e}")


    def sell(self, info, md_name, amount='x'):
        print('sell:', info, md_name, amount)
        info['매도번호'] = md_name
        info['매도시각'] = datetime.today().strftime("%H%M%S")
        code = info['종목코드']
        try:
            info2 = next(item for item in self.parent.balance if item['종목코드'] == str(code).zfill(6))
            print(info2)

        except:
            print(f'종목코드 {code}에 대한 매도 주문을 실행할 수 없습니다. ')
            return

        try:
            if amount == 'x':
                print(code, "전량 매도 주문")
                amount = info2['보유수량']

            self.send_order('send_sell_order', '8888', '2', code, amount, '0', '03')

            if md_name == 'S03' and md_name == 'S09' and md_name == 'S08':
                code = str(info['종목코드']).zfill(6)
                self.k.kiwoom.dynamicCall("SetRealRemove(QString, QString)", str(info['화면번호']), code)
                print(f'{info["종목명"]} 종목에 대한 실시간 데이터 수집을 중단합니다.')
                del self.parent.real_data[code]
                del self.parent.real_data2[code]
                del self.parent.data[code]
                del self.parent.vi_test[code]
                self.parent.alarm_data.remove(info)
                self.parent.rg_code.remove(code)

            self.wait(5)
            self.tw1_info()

        except Exception as e:
            print('sell ERROR: ', e)

    def get_tw3(self):
        rows = self.parent.tw3.rowCount()
        cols = self.parent.tw3.columnCount()
        data = []

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.parent.tw3.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        headers = [self.parent.tw3.horizontalHeaderItem(i).text() for i in range(cols)]
        df = pd.DataFrame(data, columns=headers)
        return df


    def update_tw2(self):
        try:
            df = self.get_tw3()
            df = df[df['거래상태'] == '매도']
            sec_list = list(set(df['섹터명']))

            sector_view = {}
            for sec in sec_list:
                df_sec = df[df['섹터명'] == sec]
                for k in range(len(df_sec)):
                    if sec in sector_view:
                        sector_view[sec][0] += int(df_sec['총금액'].iloc[k])-int(df_sec['수익금액'].iloc[k])
                        sector_view[sec][1] += int(df_sec['수익금액'].iloc[k])

                    else:
                        sector_view[sec] = [int(df_sec['총금액'].iloc[k])-int(df_sec['수익금액'].iloc[k]), int(df_sec['수익금액'].iloc[k])]

            total_p = 0
            self.parent.tw2.setRowCount(0)
            for item in sector_view.items():
                sector = item[0]
                p = item[1][0]
                p_r = item[1][1]
                if p:
                    total_p += int(p_r)
                    self.add_sector_view(
                        [sector, str(format(p, ',')) + '원', str(format(int(p_r), ',')) + '원',
                         str(format(round(p_r / p * 100, 2), ',')) + '%'])
                else:
                    self.add_sector_view([sector, '0원', '0원', '0%'])


            if self.parent.org_depo:
                # rate = round(total_p / self.parent.org_depo * 100, 2) * int(self.parent.v2.text()) / 100
                rate = round(total_p / self.parent.org_depo * 100 * 100 / int(self.parent.v2.text()), 2)

                # print(f"현재 총 실현 손익은 {total_p}원 / 원금 대비 {rate}%입니다.")
                self.parent.tw1.setItem(0, 5, QTableWidgetItem(format(total_p, ',') + '원'))
                self.parent.tw1.setItem(0, 6, QTableWidgetItem(str(rate) + '%'))


        except Exception as e:
            print(f"sector_view_update Error: {e}")


    def basic_ms(self, info):
        # 잔고가 없는 경우 한도를 고려한 전체 금액에 대해 매수 실행
        try:
            name = info['종목명']
            if not self.parent.balance:
                print(f"매수 보유 종목 X : {name}에 대한 매수를 실행합니다.")
                self.ms1(info)
            else:
                print(f"매수 보유 종목 O : {name}에 대한 분할 매수를 시작합니다.")
                # info['분할매수'] = [datetime.today().strftime('%H%M%S'), len(self.parent.balance)]
                self.ms2(info)
        except Exception as e:
            print(f"basic ms Error: {e}")

    def wait(self, sec):
        msec = int(sec*1000)
        loop = QEventLoop()
        QTimer.singleShot(msec, loop.quit)
        loop.exec_()

    def sp(self, yc, c):
        return round(((c - yc) / yc * 100), 2)

    def diff_from_now(self, hhmmss_int):
        hhmmss_int = int(hhmmss_int)
        # 현재 시각
        now = datetime.now()

        # HHMMSS 분해
        h = hhmmss_int // 10000
        m = (hhmmss_int % 10000) // 100
        s = hhmmss_int % 100

        # 오늘 날짜의 입력 시각 생성
        input_time = datetime(now.year, now.month, now.day, h, m, s)

        # 차이 계산 (초 단위 정수)
        diff = int((now - input_time).total_seconds())
        return diff

    # n분 기울기 계산 함수
    def incline(self, df, n):
        try:
            s = df['종가'].iloc[:n].mean()
            e = df['종가'].iloc[10:n+10].mean()
            a = round((s - e) * 10000 / (s * 10), 1)
            return a
        except:
            return ''


    def cal_real_profit(self, buy_price, sell_price, quantity):
        buy_price = int(buy_price)
        sell_price = int(sell_price)
        quantity = int(quantity)
        total_buy = buy_price * quantity
        total_sell = sell_price * quantity

        buy_fee = total_buy * 0.00015
        sell_fee = total_sell * 0.00015
        tax = total_sell * 0.0015

        net_buy = total_buy + buy_fee
        net_sell = total_sell - sell_fee - tax

        profit = net_sell - net_buy
        profit_rate = (profit / net_buy) * 100

        return [round(profit_rate, 2), int(profit)]


    def get_margin_rate(self, code):
        r = self.k.kiwoom.dynamicCall("GetMasterStockState(QString)", code)
        r = r.split('|')[0].replace('증거금', '').replace('%', '')
        if r == '20' or r == '30':
            r = '40'
        return int(r)


    def get_order(self):
        print(f"[get_order] 요청 시작")
        self.order_data = []
        return self.request_tr_with_retry("주문정보", {
            "계좌번호": self.parent.account_number,
            "전체종목구분": "0",
            "체결구분": "0",
            "매매구분": "0"
        }, "opt10075", "2004")

    def get_min_chart(self, code):
        print(f"[get_min_chart] {code} 요청 시작")
        df = self.request_tr_with_retry("분봉차트", {
            "종목코드": code+'_AL',
            "틱범위": "1",
            "수정주가구분": "1"
        }, "opt10080", "2001")
        if not len(df):
            df = self.request_tr_with_retry("분봉차트", {
                "종목코드": code+'_AL',
                "틱범위": "1",
                "수정주가구분": "1"
            }, "opt10080", "2001")
        col = ['시간', '시가', '고가', '저가', '종가', '거래량']
        dft = pd.DataFrame(df, columns=col)
        return dft

    def get_total_depo(self):
        print(f"[get_total_depo] 요청 시작")
        return self.request_tr_with_retry("총자산조회", {
            "계좌번호": self.parent.account_number,
            "상장폐지조회구분": "0",
            "비밀번호입력매체구분": "00",
            "거래소구분": "KRX"
        }, "opw00004", "2003")

    def get_deposit(self):
        print(f"[get_deposit] 요청 시작")
        return self.request_tr_with_retry("주문가능금액조회", {
            "계좌번호": self.parent.account_number,
            "비밀번호입력매체구분": "00",
            "조회구분": "2"
        }, "opw00001", "0004")

    def tw1_info(self):
        print(f'[메인 view] 업데이트')
        return self.request_tr_with_retry("계좌평가잔고내역요청", {
            "계좌번호": self.parent.account_number,
            "비밀번호입력매체구분": "00",
            "조회구분": "2"
        }, "opw00018", "2019")



    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        tr_data_cnt = self.k.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
        print(sRQName)
        if sRQName == "분봉차트":
            dl = []
            self.tr_data = []
            for i in range(tr_data_cnt):
                t = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                  "체결시간").strip())
                if str(t)[8:] == '153500':
                    continue

                d = str(t)[:8]
                if d not in dl:
                    dl.append(d)
                if len(dl) >= 3:
                    break

                op = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                   "시가").strip().lstrip('+').lstrip('-'))
                hp = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                   "고가").strip().lstrip('+').lstrip('-'))
                lp = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                   "저가").strip().lstrip('+').lstrip('-'))
                cp = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                   "현재가").strip().lstrip('+').lstrip('-'))
                ta = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                   "거래량").strip())
                self.tr_data.append([t, op, hp, lp, cp, ta])

        elif sRQName == "총자산조회":
            self.tr_data = ''
            total_depo = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "예탁자산평가액")
            self.tr_data = int(total_depo)

        elif sRQName == "주문가능금액조회":
            self.tr_data = ''
            depo = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "100%종목주문가능금액")
            self.tr_data = int(depo)

        elif sRQName == "주문정보":
            self.tr_data = []
            for i in range(tr_data_cnt):
                code = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목코드").strip()
                code_name = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명").strip()
                order_status = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문상태").strip()
                order_quantity = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문수량").strip())
                executed_quantity = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "체결량").strip())
                not_executed_quantity = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "미체결수량").strip())
                order_price = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "체결가").strip())
                ordered_at = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "시간").strip()
                buy_or_sell = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문구분").strip().lstrip('+').lstrip('-')

                self.tr_data.append({
                    '종목코드': code,
                    '종목명': code_name,
                    '주문상태': order_status,
                    '주문수량': order_quantity,
                    '체결가': order_price,
                    '체결량': executed_quantity,
                    '미체결수량': not_executed_quantity,
                    '주문시간': ordered_at,
                    '주문구분': buy_or_sell
                })

        elif sRQName == "계좌평가잔고내역요청":
            data = []
            totalBuyingPrice = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총매입금액"))
            currentTotalPrice = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총평가금액"))
            total_profit_loss_rate = float(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총수익률(%)"))
            self.parent.tw1.setItem(0, 2, QTableWidgetItem(format(totalBuyingPrice, ',')+'원'))
            self.parent.tw1.setItem(0, 3, QTableWidgetItem(format(currentTotalPrice, ',')+'원'))
            self.parent.tw1.setItem(0, 4, QTableWidgetItem(f'{total_profit_loss_rate/100}%'))

            tr_data_cnt = self.k.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            for i in range(tr_data_cnt):
                code = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목번호").strip()[1:]
                name = self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명").strip()
                qty = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "보유수량").strip())
                avg_price = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입가").strip())
                return_rate = round(float(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "수익률(%)").strip())/100, 2)
                current_price = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "현재가").strip())
                purchase_amt = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입금액").strip())
                eval_amt = int(self.k.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "평가금액").strip())
                data.append({
                    '종목명': name,
                    '종목코드': code,
                    '보유수량': qty,
                    '매입가': avg_price,
                    '수익률': return_rate,
                    '현재가': current_price,
                    '매입금액': purchase_amt,
                    '평가금액': eval_amt
                })

            self.parent.balance = data
            print('보유 잔고 현황:', data)


        if self.tr_event_loop:
            self.tr_event_loop.exit()

        self.wait(1)


    def send_order(self, rqname, screen_no, order_type, code, order_quantity, order_price, order_classification, origin_order_number=""):
        order_result = self.k.kiwoom.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",[rqname, screen_no, self.parent.account_number, order_type, code, order_quantity, order_price,order_classification, origin_order_number])
        return order_result

    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        print("[Kiwoom] _on_receive_msg is called {} / {} / {} / {}".format(screen_no, rqname, trcode, msg))

    def _on_chejan_slot(self, s_gubun, n_item_cnt, s_fid_list):
        try:
            print("[Kiwoom] _on_chejan_slot is called {} / {} / {}".format(s_gubun, n_item_cnt, s_fid_list))
            def get_fid(fid):
                return self.k.kiwoom.dynamicCall("GetChejanData(int)", fid).strip()

            if s_gubun == "0":  # 주문 체결
                fid1 = self.realType.REALTYPE["주문체결"]['종목코드']
                code = get_fid(fid1).lstrip("A")
                fid2 = self.realType.REALTYPE["주문체결"]['주문상태']
                b = get_fid(fid2).strip()
                fid3 = self.realType.REALTYPE["주문체결"]['매도수구분']
                c = get_fid(fid3).strip()

                fid7 = self.realType.REALTYPE["주문체결"]['주문수량']
                g = get_fid(fid7).strip()

                fid5 = self.realType.REALTYPE["주문체결"]['체결가']
                e = get_fid(fid5).strip()

                fid6 = self.realType.REALTYPE["주문체결"]['체결량']
                f = get_fid(fid6).strip()

                info = next((data for data in self.parent.alarm_data if data['종목코드'] == code))

                # 매수 체결 시 첫매수가 정보가 없으면 등록
                if c == '2' and b == "체결" and (info['1차매수가'] == 9999999):
                    print(f"종목코드 {code}의 1차매수가: {int(e)}")
                    info['1차매수가'] = int(e)

                # 매수 체결 시 주문수량 = 체결량 일 때 실시간 잔고 반영
                if c == '2' and b == "체결" and g == f:
                    print(f"{int(e)} * {int(f)} = {int(e)*int(f)}")
                    self.asset -= int(e)*int(f)

                if c == '1' and b == "체결" and g == f:
                    # 매도 데이터 갱신
                    print(info)
                    real_profit = self.cal_real_profit(info['매수가'], e, f)
                    print(real_profit)
                    self.update_tw3([datetime.today().strftime('%H%M%S'), '매도', e, f, int(e)*int(f),
                                     info['섹터명'], info['종목명'], '', real_profit[0], real_profit[1], info['매도번호']])



            elif s_gubun == "1": # 잔고변동
                fid1 = self.realType.REALTYPE["잔고"]['종목코드']
                code = get_fid(fid1).lstrip("A")

                fid3 = self.realType.REALTYPE["잔고"]['보유수량']
                a = get_fid(fid3)

                fid6 = self.realType.REALTYPE["잔고"]['매입단가']
                b = get_fid(fid6)

                fid7 = self.realType.REALTYPE["잔고"]['총매입가']
                c = get_fid(fid7)

                fid8 = self.realType.REALTYPE["잔고"]['매도매수구분']
                d = get_fid(fid8)


                # 매수 데이터 갱신
                if d == '2':
                    info = next((data for data in self.parent.alarm_data if data['종목코드'] == code))

                    last_row = self.get_last_row_tw3()
                    if last_row:
                        if last_row[1] == "매수" and last_row[6] == info['종목명']:
                            row_count = self.parent.tw3.rowCount()
                            self.parent.tw3.removeRow(row_count - 1)

                    self.update_tw3([datetime.today().strftime("%H%M%S"), "매수", b, a, c, info['섹터명'], info['종목명'], info['매수전략']])
                    info['매수가'] = b
                    info['매수수량'] = a

        except Exception as e:
            print(e)

    def add_minutes(self, date_str, time_int, minutes):
        dt = datetime.strptime(f"{date_str}{str(time_int).zfill(4)}", "%Y%m%d%H%M")
        dt += timedelta(minutes=minutes)
        return int(dt.strftime("%H%M"))

    def realdata_slot(self, sCode, sRealType, sRealData):
        try:
            if sRealType == "주식체결":
                fid1 = self.realType.REALTYPE[sRealType]['체결시간']
                a = self.k.kiwoom.dynamicCall("GetCommRealData(QString, int)", sCode, fid1)

                fid2 = self.realType.REALTYPE[sRealType]['현재가']
                b = self.k.kiwoom.dynamicCall("GetCommRealData(QString, int)", sCode, fid2)
                b = abs(int(b))

                fid3 = self.realType.REALTYPE[sRealType]['전일대비']
                c = self.k.kiwoom.dynamicCall("GetCommRealData(QString, int)", sCode, fid3)
                c = abs(int(c))

                fid4 = self.realType.REALTYPE[sRealType]['등락율']
                d = self.k.kiwoom.dynamicCall("GetCommRealData(QString, int)", sCode, fid4)
                d = float(d)

                fid5 = self.realType.REALTYPE[sRealType]['거래량']
                e = self.k.kiwoom.dynamicCall("GetCommRealData(QString, int)", sCode, fid5)
                e = abs(int(e))

                self.parent.data[sCode] = b



                # 분봉 데이터 포함 여부 확인
                hj_time = self.today+a[:4]+'00'
                info = next(d for d in self.parent.alarm_data if (d.get('종목코드') == sCode))
                min_data = info['분봉데이터']

                if int(hj_time) not in list(min_data['시간']):
                    new_row = {
                        '시간': int(hj_time),
                        '시가': b,
                        '고가': b,
                        '저가': b,
                        '종가': b,
                        '거래량': e,
                        '등락률': d
                    }
                    info['분봉데이터'] = pd.concat([pd.DataFrame([new_row]), min_data], ignore_index=True)

                else:
                    if b > min_data.loc[0, '고가']:
                        min_data.loc[0, '고가'] = b

                    if b < min_data.loc[0, '저가']:
                        min_data.loc[0, '저가'] = b

                    min_data.loc[0, '종가'] = b
                    min_data.loc[0, '등락률'] = d
                    min_data.loc[0, '거래량'] += e

        except Exception as e:
            pass
            # print('realdata_slot ERROR: ', e)


    def update_tw3(self, row_data):
        row_position = self.parent.tw3.rowCount()
        self.parent.tw3.insertRow(row_position)
        for col, value in enumerate(row_data):
            item = QTableWidgetItem(str(value))
            self.parent.tw3.setItem(row_position, col, item)

    def get_last_row_tw3(self):
        row_count = self.parent.tw3.rowCount()
        if row_count == 0:
            return []

        last_row = row_count - 1
        column_count = self.parent.tw3.columnCount()

        row_data = []
        for col in range(column_count):
            item = self.parent.tw3.item(last_row, col)
            row_data.append(item.text() if item else "")

        return row_data

    # 가장 최근의 매매 수익 여부를 반환하는 함수
    def recent_trade(self, name):
        order = self.get_order()
        self.wait(0.5)
        try:
            r_ms = next(item for item in order if (item['종목명'] == name) & (item['주문구분'] == '매수'))['체결가']
            r_md = next(item for item in order if (item['종목명'] == name) & (item['주문구분'] == '매도'))['체결가']
            if r_ms < r_md:
                return True
            else:
                return False
        except:
            return False

    def telegram(self, text):
        url = f'https://api.telegram.org/bot{self.token}/sendMessage'
        payload = {'chat_id': self.chat_id, 'text': text}
        req = requests.post(url, data=payload)

    def add_sector_view(self, row_data):
        row_position = self.parent.tw2.rowCount()
        self.parent.tw2.insertRow(row_position)
        for col, value in enumerate(row_data):
            item = QTableWidgetItem(str(value))
            self.parent.tw2.setItem(row_position, col, item)

    def msg_pop(self, title, content):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(content)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def request_tr_with_retry(self, rqname, input_values, tr_code, screen_no, max_retry=5):
        for attempt in range(max_retry):
            self.tr_event_loop = QEventLoop()
            self.tr_data = None

            timer = QTimer()
            timer.timeout.connect(self.tr_event_loop.exit)
            timer.setSingleShot(True)
            timer.start(8000)

            for k, v in input_values.items():
                self.k.kiwoom.dynamicCall("SetInputValue(QString, QString)", k, v)

            self.k.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, tr_code, 0, screen_no)
            self.tr_event_loop.exec_()

            if timer.isActive():
                timer.stop()
                print(f"[{rqname}] 요청 성공 (시도 {attempt + 1})")
                return self.tr_data
            else:
                print(f"[{rqname}] ⏱ 타임아웃 발생 (시도 {attempt + 1})")

        return None


    def get_shg(self, prev_close):
        def get_tick_unit(price):
            if price < 2000:
                return 1
            elif price < 5000:
                return 5
            elif price < 20000:
                return 10
            elif price < 50000:
                return 50
            elif price < 200000:
                return 100
            elif price < 500000:
                return 500
            else:
                return 1000

        limit_price = int(prev_close * 1.3)  # 30% 상승 후 소수점 절삭
        tick = get_tick_unit(limit_price)
        upper_price = (limit_price // tick) * tick  # 호가단위에 맞춰 절삭
        return upper_price