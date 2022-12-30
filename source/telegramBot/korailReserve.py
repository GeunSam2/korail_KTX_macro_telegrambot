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
    
    def login(self, username, password):
        self.korailObj = k2mKorail(username, password,  auto_login=False)
        self.loginSuc = self.korailObj.login()
        return self.loginSuc
    
    def reserve(self, depDate, srcLocate, dstLocate, depTime='000000', trainType=TrainType.KTX, special=ReserveOption.GENERAL_FIRST, chatId="", maxDepTime="2400"):
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
                timeL = "".join(str(trains[0]).split("(")[1].split("~")[0].split(":"))
                if (int(timeL) >= int(maxDepTime)): trains = []
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
            # print ("{} {}".format(currentTime, self.reserveInfo))
            time.sleep(self.interval)

            #Out of While loop
        if (self.chatId == ""):
            return reserveOne
        else:
            self.telebotResponse(reserveOne)
            return None
    
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
