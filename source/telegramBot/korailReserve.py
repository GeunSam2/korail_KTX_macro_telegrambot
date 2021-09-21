import requests
import time
from bs4 import BeautifulSoup as bs
import sys
from .korail2.korail2 import Korail as k2mKorail
from .korail2.korail2 import ReserveOption, TrainType, SoldOutError, NoResultsError

sys.setrecursionlimit(10**7)

class Korail(object):
    korailObj = ""
    s = requests.session()

    reserveInfo = {}
    reserveInfo['depDate'] = ""
    reserveInfo['depTime'] = ""
    reserveInfo['srcLocate'] = ""
    reserveInfo['dstLocate'] = ""
    reserveInfo['special'] = ""
    reserveInfo['reserveSuc'] = False
    
    interval = 1 ##sec 분당 100회 이상이면 이상탐지에 걸림
    
    loginSuc = False
    txtGoHour = "000000"
    specialVal = ""
    chatId = "" ##Telegram Chat bot에서 callback 받을때 전달 받아야 함
    
    def __init__(self):
        self.s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
        self.s.headers["Upgrade-Insecure-Requests"] = "1"
        self.s.headers["Referer"] = "http://www.letskorail.com/"
        self.s.headers["Sec-Fetch-Dest"] = "document"
        self.s.headers["Sec-Fetch-User"] = "?1"
        self.s.headers["Sec-Fetch-Mode"] = "navigate"
        self.s.headers["Sec-Fetch-Site"] = "cross-site"
        self.s.headers["Accept-Encoding"] = "gzip, deflate, br"
        self.s.headers["Origin"] = "http://www.letskorail.com"
    
    # def checkInfo(self):
    #     check1 = (self.reserveInfo['depDate'] == "")
    #     check2 = (self.reserveInfo['srcLocate'] == "")
    #     check3 = (self.reserveInfo['dstLocate'] == "")
    #     if (check1 and check2 and check3):
    #         raise exception("초기값 설정이 안되었습니다. setInfo() 함수를 호출하세요.")
    #     elif (not self.loginSuc):
    #         raise exception("초기값 설정이 안되었습니다. login()함수를 호출하세요.")
        
    
    def login(self, username, password):
        #####
        # korail2 모듈 사용 전 코드
        #####
        # loginUrl = "https://www.letskorail.com/korail/com/loginAction.do"
        # loginData = {
        #     "selInputFlg": 4,
        #     "radIngrDvCd": 2,
        #     "hidMemberFlg": 1,
        #     "txtDv": 2,
        #     "UserId": username,
        #     "UserPwd": password
        # }
        # login = self.s.post(loginUrl, data=loginData)
        # #로그인 성공시 javascript 구문이 짦게 나오고 아래 변수가 유일하게 섞여있음.
        # if ("strWebPwdCphdAt" in login.text):
        #     print ("로그인 성공")
        #     self.loginSuc = True
        # else:
        #     print ("로그인 실패")
        #     self.loginSuc = False
        self.korailObj = k2mKorail(username, password,  auto_login=False)
        self.loginSuc = self.korailObj.login()
        return self.loginSuc
            
    # def setInfo(self, depDate, srcLocate, dstLocate, depTime='000000', trainType=TrainType.KTX, special=ReserveOption.GENERAL_FIRST, chatId=""):
    #     self.reserveInfo['depDate'] = depDate
    #     self.reserveInfo['srcLocate'] = srcLocate
    #     self.reserveInfo['dstLocate'] = dstLocate
    #     self.reserveInfo['depTime'] = depTime
    #     self.reserveInfo['trainType'] = trainType
    #     self.reserveInfo['special'] = special #Option Default "N" => Don't reserve Special Seat
    #     self.chatId = chatId ##Telegram Chat bot에서 callback 받을때 전달 받아야 함
    
    def reserve(self, depDate, srcLocate, dstLocate, depTime='000000', trainType=TrainType.KTX, special=ReserveOption.GENERAL_FIRST, chatId=""):
        # while (not self.reserveInfo['reserveSuc']):
        #     self.getTickets()
        #     self.reserveInfo['reserveSuc'] = False
        #     currentTickets = self.ticketCount
        #     tdsData, scriptItems, txtGoHour = self.reserveData()

        #     if (len(tdsData) == 0):
        #         if (self.chatId == ""):
        #             return "wrong"
        #         else:
        #             self.telebotResponse("wrong")
        #             return None
        #     #페이지 기준 데이터로 예약 가능 여부 확인 후 예매 트리거
        #     for count, dumy in enumerate(tdsData):
                
        #         #예약가능 여부 뽑기
        #         items = dumy.find_all('td')
        #         try:
        #             seatSpecial = items[4].img['alt'] ##특등석 예약가능 여부
        #             seatNormal = items[5].img['alt']  ##일반석 예약가능 여부
        #         except:
        #             ##특실이 없는 열차(ktx 아닌경우)
        #             seatSpecial = "예약불가" 
        #             seatNormal = "예약불가"  

        #         #예약 필요 정보 뽑기
        #         scriptItem = scriptItems[count].string.replace("\r\n","").replace("\t","").replace(" ","").split('"')[1:-1]
        #         while ',' in scriptItem :
        #             scriptItem.remove(',')
        #         depCode, arrCode, depDate, depTime = scriptItem[18], scriptItem[20], scriptItem[0], scriptItem[29]
        #         self.reserveInfo['depTime'] = depTime

        #         #일반좌석 예매
        #         if (seatNormal == "예약하기"):

        #             req = self.reserveRequests(depCode, arrCode, depDate, depTime, "1")
        #             self.getTickets()
        #             if (self.ticketCount > currentTickets):
        #             #예약현황 리스트 수 확인해서 성공 여부 체크
        #                 print ("Nomal Reserved")
        #                 self.reserveInfo['special'] = 1
        #                 self.reserveInfo['reserveSuc'] = True
        #             else :
        #                 print ("Nomal Reserved Fail")
        #             break

        #         #특별좌석 예매
        #         elif (seatSpecial == "예약하기"):
        #             if (self.specialVal == "Y") : 

        #                 req = self.reserveRequests(depCode, arrCode, depDate, depTime, "2")
        #                 self.getTickets()
        #                 if (self.ticketCount > currentTickets):
        #                 #예약현황 리스트 수 확인해서 성공 여부 체크
        #                     print ("Special Reserved")
        #                     self.reserveInfo['special'] = 2
        #                     self.reserveInfo['reserveSuc'] = True
        #                 else :
        #                     print ("Special Reserved Fail")
        #                 break

        self.reserveInfo['depDate'] = depDate
        self.reserveInfo['srcLocate'] = srcLocate
        self.reserveInfo['dstLocate'] = dstLocate
        self.reserveInfo['depTime'] = depTime
        self.reserveInfo['trainType'] = trainType
        self.reserveInfo['special'] = special #Option Default "N" => Don't reserve Special Seat
        self.chatId = chatId ##Telegram Chat bot에서 callback 받을때 전달 받아야 함
        reserveOne = None
        while not reserveOne:
            try:
                trains = self.korailObj.search_train(srcLocate, dstLocate, depDate, depTime, train_type=trainType)
            except NoResultsError:
                trains = []
            
            for train in trains:
                print (f'열차 발견 : {train} <- 에 대한 예약을 시작합니다.')
                try:
                    reserveOne = self.korailObj.reserve(train, option=special)
                    if (reserveOne):
                        self.reserveInfo['reserveSuc'] = True
                        break
                except SoldOutError:
                    print ('발견한 열차 놓침...')


            #Sleep
            currentTime = time.strftime('%H:%M:%S', time.localtime(time.time()))
            print ("{} {}".format(currentTime, self.reserveInfo))
            time.sleep(self.interval)

            #Out of While loop
        if (self.chatId == ""):
            return reserveOne
        else:
            self.telebotResponse(reserveOne)
            return None

    # def reserveRequests(self, depCode, arrCode, depDate, depTime, special):
    #     # korail2 모듈 사용 전에 사용하던 예약 요청 함수

    #     # 실질적인 예약 기능
    #     # reservation server checks referer.
    #     self.s.headers['Referer'] = 'http://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do'
    #     url = 'http://www.letskorail.com/ebizprd/EbizPrdTicketPr12111_i1.do'
    #     data= {
    #         # 15: 기본
    #         # 18: 2층석
    #         # 19: 유아동반
    #         # 19: 편한대화(중복?)
    #         # 21: 휠체어
    #         # 28: 전동휠체어
    #         # 29: 교통약자(없어진듯)
    #         # 30: 레포츠보관함
    #         # 31: 노트북
    #         # 32: 자전거거치대
    #         # XX: 수유실인접
    #         "txtSeatAttCd4": "015",

    #         "txtTotPsgCnt": "1", #???????????????머선값이고??
    #         "txtPsgTpCd1": "1", # ??? - 단체예약, 개인예약 구분이라는데...
    #         "txtCompaCnt1": "1",  #인원

    #         # 1101: 개인예약
    #         # 1102: 예약대기
    #         # 1103: SEATMAP예약
    #         "txtJobId": "1101", 

    #         "txtJrnyCnt": "1", # 환승 횟수 (1이면 편도)
    #         "txtPsrmClCd1": special,  #일반실1, 특실2
    #         "txtJrnySqno1": "001", # ???
    #         "txtJrnyTpCd1": "11",  # 편도
    #         "txtDptDt1": depDate, #날짜
    #         "txtDptRsStnCd1": depCode, # 출발역 코드
    #         "txtDptTm1": depTime,  #출발 시간
    #         "txtArvRsStnCd1": arrCode, # 도착역 코드
    #         "txtTrnClsfCd1": "00" # 열차 종류(Train Class Code인듯)
    #     }    
    #     req = self.s.post(url, data=data)
    #     return req
    
    # def getTickets(self):
    # korail2 모듈 사용 전 사용하던 예약된 티켓 조회 

    #     ticketUrl="https://www.letskorail.com/ebizprd/EbizPrdTicketpr13500W_pr13510.do"
    #     req = self.s.get(ticketUrl)
    #     soup = bs(req.text, 'html.parser')
    #     ticketCountAll = len(soup.find_all('input', {"name": "radPnr", "type": "radio"})) ##마이페이지에 있는 티켓 갯수
    #     ticketCountYet = 0
    #     labels = []
    #     for num in range(ticketCountAll):
    #         spansSoup = soup.find_all('td', {"class": "txt_red left_black"})[num]
    #         span = spansSoup.text.strip()
    #         if ("결제완료" in span):
    #             pass
    #             #결제 완료에 대한 추가 기능 생각나면 넣자
    #         else:
    #             print ("예약티켓")

    #             labelSoup = soup.find_all('label', {"for": "radio{}".format(num)})
    #             ticketCountYet += 1
    #             labels.append([])
    #             for label in labelSoup:
    #                 labels[-1].append(label.text)
                    
    #     #예매티켓 갯수 갱신 (예매 확인용)
    #     self.ticketCount = ticketCountYet
        
    #     #예매티켓에 대한 정보 array로 전달
    #     return labels
    
    ##텔레그램 봇 용 callback
    def telebotResponse(self, reserveInfo):
        print (reserveInfo)
        result = self.reserveInfo['reserveSuc']
        chatId = self.chatId
        
        if (result == "wrong"):
            msg = "차편을 찾을 수 없거나, 검색에 문제가 생겼어요. 처음부터 다시 시도해 주세요."
        elif (result):
            msg = f"""
열차 예약에 성공했습니다!!
예약에 성공한 열차 정보는 다음과 같습니다.
===================
{reserveInfo}
===================

20분내에 사이트에서 결제를 완료하지 않으면 예약이 취소되니 서두르세요!
https://www.letskorail.com/ebizprd/EbizPrdTicketpr13500W_pr13510.do?
"""
        else :
            msg = """
알수 없는 오류로 예매에 실패했습니다. 처음부터 다시 시도해주세요.

[문제가 없는데 계속 반복되는 경우, 이미 해당 열차가 예매가 되었을 수 있습니다. 사이트를 확인해주세요.]
"""
        self.telebotChangeState(chatId, msg, 0)
        return None

    
    def telebotChangeState(self, chatId, msg, status):
        #callbackUrl = "https://127.0.0.1:8080/telebot" #if you use ssl inside docker, use this
        callbackUrl = "http://127.0.0.1:8080/telebot"
        print (chatId, msg, status)
        param = {
            "chatId": chatId,
            "msg" : msg,
            "status" : status
        }
        s = requests.session()
        s.get(callbackUrl, params=param, verify=False)
        return None
