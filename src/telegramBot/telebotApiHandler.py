from .korail2.korail2 import ReserveOption, TrainType
from flask import Flask, request, jsonify, make_response
from flask_restful import marshal_with, Resource, reqparse, fields
from .korailReserve import Korail
from multiprocessing import Process
import requests
import time
import base64
import json
import os
import subprocess
import signal

class Index(Resource):
    
    s = requests.session()
    BOTTOKEN = os.environ.get('BOTTOKEN')
    sendUrl = "https://api.telegram.org/bot{}".format(BOTTOKEN)
    
    #userDict : Use like DB.
    # {
    #   123123: {
    #     "inProgress": True,
    #     "lastAction": "",
    #     "userInfo": { "korailId": "010-1111-1111", "korailPw": "123123" },
    #     "trainInfo": {"srcLocate":"광명", "dstLocate": "광주송정", "depDate": "20210204"}
    #     "pid": 9999999
    #   }
    # }
    userDict = {}

    #runningStatus : Use like DB.
    # {
        # 123123: {
        #     "pid": 9999999,
        # } 
    # }
    runningStatus = {}

    #Group for get notification
    subscribes = []
    
    def manageProgress(self, chatId, action, data=""):
        #     !!lastAction!!
        #     0 : init
        #     1 : started
        #     2 : startAccepted
        #     3 : idInputSuc
        #     4 : pWInputSuc
        #     5 : dateInputSuc
        #     6 : srcLoateInputSuc
        #     7 : dstLocateInputSuc
        #     8 : depTimeInputSuc
        #     9 : maxDepTimeInputSuc
        #     10 : trainTypeInputSuc
        #     11 : specialInputSuc
        #     12 : findingTicket
        if (action == 0):
            self.userDict[chatId]={
                "inProgress": False,
                "lastAction" : action,
                "userInfo" : {
                    "korailId": "no-login-yet", 
                    "korailPw": "no-login-yet"
                },
                "trainInfo" : {},
                "pid": 9999999
            }
            return

        if (len(self.runningStatus) > 0 and chatId not in dict.keys(self.runningStatus)):
            data = "현재 다른 유저가 이용중입니다. 급하면 관리자에게 문의하세요."
            self.sendMessage(chatId, data)
            return

        if (action == 1):
            self.startAccept(chatId, data)
        elif (action == 2):
            self.inputId(chatId, data)
        elif (action == 3):
            self.inputPw(chatId, data)
        elif (action == 4):
            self.inputDate(chatId, data)
        elif (action == 5):
            self.inputSrcLoate(chatId, data)
        elif (action == 6):
            self.inputDstLoate(chatId, data)
        elif (action == 7):
            self.inputDepTime(chatId, data)
        elif (action == 8):
            self.inputMaxDepTime(chatId, data)
        elif (action == 9):
            self.inputTrainType(chatId, data)
        elif (action == 10):
            self.inputSpecial(chatId, data)
        elif (action == 11):
            self.startReserve(chatId, data)
        else :
            ##
            data = "이상이 발생했습니다. /cancel 이나 /start 를 통해 다시 프로그램을 시작해주세요."
            self.sendMessage(chatId, data)
        return None
    
    def getUserProgress(self, chatId):
        if (chatId in self.userDict):
            progressNum = self.userDict[chatId]["lastAction"]
        else:
            self.manageProgress(chatId, 0)
            progressNum = 0
        inProgress = self.userDict[chatId]["inProgress"]
        return inProgress, progressNum
    
    def post(self):
        # print (json.dumps(request.json, sort_keys=True, indent=4))
        if ("edited_message" in request.json):
            pass
            return make_response("OK")
        if ("my_chat_member" in request.json):
            pass
            return make_response("OK")
        try:
            initFlag = False
            getText = request.json['message']['text'].strip()
        except:
            initFlag = True
            getText = "코레일 예약봇입니다.\n시작하시려면 /start 를 입력해주세요."
        chatId = request.json['message']['chat']['id']
        chatId = int(chatId)
        
        inProgress, progressNum = self.getUserProgress(chatId)
        print ("CHATID : {} , TEXT : {}, InProgress : {}, Progress : {}".format(chatId, getText, inProgress, progressNum))
        
        if (getText == "/cancel"):
            self.cancelFunc(chatId)
            return make_response("OK")
        elif (progressNum == 12):
            self.alreadyDoing(chatId)
            return make_response("OK")
        
        if (getText == "/start"):
            self.startFunc(chatId)
        elif (getText == "/subscribe"):
            self.subscribe(chatId)
        elif (getText == "/status"):
            self.getStatusInfo(chatId)
        elif (getText == "/cancelall"):
            self.cancelAll(chatId)
        elif (getText == "/allusers"):
            self.getAllUsers(chatId)
        elif (getText.split(' ')[0] == '/broadcast'):
            self.broadCast(getText)
        elif (getText == "/help"):
            self.returnHelp(chatId)
        elif (getText[0] == "/"):
            getText = "잘못된 명령어 입니다."
            self.sendMessage(chatId, getText)
        else :
            if (inProgress):
                self.manageProgress(chatId, progressNum, getText)
            else:
                if (initFlag):
                    self.sendMessage(chatId, getText)
                else :
                    msg = "[진행중인 예약프로세스가 없습니다]\n/start 를 입력하여 작업을 시작하세요.\n"
                    self.sendMessage(chatId, msg)
        return make_response("OK")
    
    
    ##사용자에게 메시지 보내기
    def sendMessage(self, chatId, getText):
        sendUrl = "{}/sendMessage".format(self.sendUrl)
        params = {
            "chat_id" : chatId,
            "text" : getText
        }
        self.s.get(sendUrl, params=params)
        return None
    
    def startFunc(self, chatId):
        msg = """
근삼 코레일 봇을 이용해 주셔사 감사합니다.
본 프로그램은 매진 열차 자동 예약을 위해 제작된 프로그램으로, 결제 직전의 단계인 "예약" 까지만 진행해 주며, 이후 결제는 예약이 완료된 이후 20분 내로 사용자가 직접 해주셔야 합니다.

예매 프로그램을 시작하기 위해 정보를 입력받겠습니다.
예매정보 입력은 다음 순서로 진행됩니다.
================
  1. 코레일 로그인 정보 입력
  2. 출발 희망일 입력
  3. 출발 역 입력
  4. 도착 역 입력
  *. 관리자로 바로 로그인 : 근삼이최고
================

예매 프로세스를 계속 진행하시려면 "예" 또는 "Y"를 입력해주세요.
            """
        self.userDict[chatId]["inProgress"] = True
        self.userDict[chatId]["lastAction"] = 1
        self.sendMessage(chatId, msg)
        return None
    
    def startAccept(self, chatId, data="Y"):
        if (str(data).upper() == "Y" or str(data) == "예"):
            self.userDict[chatId]["lastAction"] = 2
            msg = """
예매 진행을 계속합니다.
예매 진행중, 취소를 원하시면 /cancel 을 입력해주세요.
코레일 로그인의 위해 정보입력을 시작합니다.

(현재는 휴대폰 번호 로그인 기능만을 지원하며, 추가 기능은 이후 추가할 예정입니다.)

코레일 로그인시 사용하는 휴대전화번호를 입력해 주세요.
[ex_ 010-7537-2437] "-" 를 반드시 포함하여 입력바랍니다.
"""
        elif (str(data) == "근삼이최고"):
            username = os.environ.get("USERID")
            password = os.environ.get("USERPW")
            if (username and password):
                self.userDict[chatId]["userInfo"]["korailId"] = username
                self.userDict[chatId]["userInfo"]["korailPw"] = password
                korail = Korail()
                loginSuc = korail.login(username, password)
                print (loginSuc)
                if (loginSuc):
                    msg = """
로그인에 성공하였습니다.
예매 희망일 8자를 입력해주십시오.
(ex_ 20210124) <- 2021년 1월 24일
"""
                    self.userDict[chatId]["lastAction"] = 4
                else:
                    self.manageProgress(chatId, 0)
                    msg = "관리자 계정으로 로그인에 문제가 발생하였습니다."
            else:
                self.manageProgress(chatId, 0)
                msg = "컨테이너에 환경변수가 초기화되지 않았습니다."
        else:
            self.manageProgress(chatId, 0)
            msg = "예매 진행을 취소합니다."
        self.sendMessage(chatId, msg)
        return None
    
    #아이디 입력 함수
    def inputId(self, chatId, data):
        if ("-" not in data):
            msg = "'-'를 포함한 전화번호를 입력해주세요. 다시 입력 바랍니다."
        else:
            self.userDict[chatId]["userInfo"]["korailId"] = data
            self.userDict[chatId]["lastAction"] = 3
            msg = """
아이디 입력에 성공하였습니다.
비밀번호를 입력해주십시오.
"""
        self.sendMessage(chatId, msg)
        return None
    
    #패스워드 입력 함수
    def inputPw(self, chatId, data):
        self.userDict[chatId]["userInfo"]["korailPw"] = data
        print (self.userDict[chatId]["userInfo"])
        username = self.userDict[chatId]["userInfo"]["korailId"]
        password = self.userDict[chatId]["userInfo"]["korailPw"]
        korail = Korail()
        loginSuc = korail.login(username, password)
        print (loginSuc)
        if (loginSuc):
            msg = """
로그인에 성공하였습니다.
예매 희망일 8자를 입력해주십시오.
(ex_ 20230101) <- 2023년 1월 1일
"""
            self.userDict[chatId]["lastAction"] = 4
            self.sendMessage(chatId, msg)
        else:
            if (str(data).upper() == "Y" or str(data) == "예"):
                self.startAccept(chatId)
            elif (str(data).upper() == "N" or str(data) == "아니오"):
                self.manageProgress(chatId, 0)
                msg = "예약이 취소되었습니다."
                self.sendMessage(chatId, msg) 
            else:
                msg = """
로그인에 실패하였습니다. 로그인에 사용한 정보는 다음과 같습니다.
==============
아이디 : {} 
암호 : 보안상 공개불가
==============
'Y'또는 '예'를 입력하시면 계정정보를 다시 입력합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
아이디를 그대로 다시 로그인 시도를 하시려면 암호를 입력하세요.

5회 이상 로그인 실패할 경우, 홈페이지를 통해 비밀번호를 재설정하셔야합니다.
""".format(username)
                self.sendMessage(chatId, msg)

        return None
    
    #출발일 입력 함수
    def inputDate(self, chatId, data):
        if (str(data).isdigit() and len(str(data)) == 8):
            self.userDict[chatId]["trainInfo"]["depDate"] = data
            self.userDict[chatId]["lastAction"] = 5
            msg = """
출발일 입력에 성공하였습니다.
출발역을 입력해주십시오.

역 정보를 참고하시려면 다음 사이트를 이용하세요. http://www.letskorail.com/ebizprd/stationKtxList.do
['역' 을 제외한 이름을 입력해주세요.]
(ex_ 광명)
"""
        else:
            msg = """
입력하신 날짜가 형식에 맞지 않습니다.
예매 희망일 8자를 입력해주십시오.
(ex_ 20210124) <- 2021년 1월 24일
"""
        self.sendMessage(chatId, msg)
        return None
        
    def inputSrcLoate(self, chatId, data):
        self.userDict[chatId]["trainInfo"]["srcLocate"] = data
        self.userDict[chatId]["lastAction"] = 6
        msg = """
출발역 입력이 완료되었습니다.
도착역을 입력해 주십시오.

역 정보를 참고하시려면 다음 사이트를 이용하세요. http://www.letskorail.com/ebizprd/stationKtxList.do
['역' 을 제외한 이름을 입력해주세요.]
(ex_ 광주송정)
"""
        self.sendMessage(chatId, msg)
        return None
    
    def inputDstLoate(self, chatId, data):

        self.userDict[chatId]["trainInfo"]["dstLocate"] = data
        self.userDict[chatId]["lastAction"] = 7
        msg = """
도착역 입력이 완료되었습니다.
열차 검색을 시작할 기준 시각정보를 입력해주세요.

형식은 HHMM (HH : 시, MM : 분)이며 0-23시 기준입니다. 반드시 4자리로 입력해 주십시오.
(ex_ 13시 5분 이후 기차만 검색 : 1305) 
"""

        self.sendMessage(chatId, msg)
        return None


    def inputDepTime(self, chatId, data):
        if (len(str(data)) == 4 and str(data).isdecimal()):
            self.userDict[chatId]["trainInfo"]["depTime"] = data
            self.userDict[chatId]["lastAction"] = 8
            msg = """
열차 검색 시작 기준 시각 입력이 완료되었습니다.
열차 검색 최대 임계 시각정보를 입력해주세요.

* 임계시각을 지정하지 않으시려면 2400을 입력하세요.(권장)

형식은 HHMM (HH : 시, MM : 분)이며 0-23시 기준입니다. 반드시 4자리로 입력해 주십시오.
(ex_ 13시 5분 이전 기차만 검색 : 1305) 
"""
        else:
            msg = """입력하신 값이 HHMM 형식에 맞지 않습니다. 다시 입력해주세요."""

        self.sendMessage(chatId, msg)
        return None

    def inputMaxDepTime(self, chatId, data):
        if (len(str(data)) == 4 and str(data).isdecimal()):
            self.userDict[chatId]["trainInfo"]["maxDepTime"] = data
            self.userDict[chatId]["lastAction"] = 9
            msg = """
기준 시각 입력이 완료되었습니다.
이용할 열차의 타입을 선택해 주십시오.

=================
1. KTX 및 KTX-산천 열차만 예약
2. 모든 열차 형식 포함하여 예약
=================

1 또는 2를 입력해 주십시오.
"""
        else:
            msg = """입력하신 값이 HHMM 형식에 맞지 않습니다. 다시 입력해주세요."""

        self.sendMessage(chatId, msg)
        return None

    def inputTrainType(self, chatId, data):
        if(str(data) in ["1","2"]):
            if (str(data) == "1"): 
                trainType = TrainType.KTX
                trainTypeShow = "KTX"
            elif (str(data) == "2"): 
                trainType = TrainType.ALL
                trainTypeShow = "ALL"
            self.userDict[chatId]["trainInfo"]["trainType"] = trainType
            self.userDict[chatId]["trainInfo"]["trainTypeShow"] = trainTypeShow
            self.userDict[chatId]["lastAction"] = 10
            msg = """
이용할 열차의 타입 입력이 완료되었습니다.
특실 예매에 대한 타입을 입력해 주십시오.

=================
1. 일반실 우선 예약
2. 일반실만 예약
3. 특실 우선 예약
4. 특실만 예약
=================

1, 2, 3, 4 중 하나를 선택해 주십시오.
"""
        else:
            msg = """입력하신 값이 1,2 중 하나가 아닙니다. 다시 입력해주세요."""
        self.sendMessage(chatId, msg)
        return None
    
    def inputSpecial(self, chatId, data):
        if(str(data) in ["1","2","3","4"]):
            if (str(data) == "1"): 
                specialInfo = ReserveOption.GENERAL_FIRST
                specialInfoShow = ReserveOption.GENERAL_FIRST
            elif (str(data) == "2"): 
                specialInfo = ReserveOption.GENERAL_ONLY
                specialInfoShow = ReserveOption.GENERAL_ONLY
            elif (str(data) == "3"): 
                specialInfo = ReserveOption.SPECIAL_FIRST
                specialInfoShow = ReserveOption.SPECIAL_FIRST
            elif (str(data) == "4"): 
                specialInfo = ReserveOption.SPECIAL_ONLY
                specialInfoShow = ReserveOption.SPECIAL_ONLY


            self.userDict[chatId]["trainInfo"]["specialInfo"] = specialInfo
            self.userDict[chatId]["trainInfo"]["specialInfoShow"] = specialInfoShow
            self.userDict[chatId]["lastAction"] = 11
            depDate = self.userDict[chatId]["trainInfo"]["depDate"]
            srcLocate = self.userDict[chatId]["trainInfo"]["srcLocate"]
            dstLocate = self.userDict[chatId]["trainInfo"]["dstLocate"]
            depTime = self.userDict[chatId]["trainInfo"]["depTime"]
            maxDepTime = self.userDict[chatId]["trainInfo"]["maxDepTime"]
            trainTypeShow = self.userDict[chatId]["trainInfo"]["trainTypeShow"]
            msg = f"""
모든 정보 입력이 완료되었습니다.
정보를 확인하십시오.
===================
출발일 : {depDate}
출발역 : {srcLocate}
도착역 : {dstLocate}
검색기준시각 : {depTime}
검색최대시각 : {maxDepTime}
열차타입 : {trainTypeShow}
특실여부 : {specialInfoShow}
===================

'Y'또는 '예'를 입력하시면 예약을 시작합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
예약 완료에 오랜 시간이 걸릴 수 있습니다.
"""
        else:
            msg = """입력하신 값이 1,2,3,4 중 하나가 아닙니다. 다시 입력해주세요."""
        self.sendMessage(chatId, msg)
        return None
    
    def startReserve(self, chatId, data):
        if (str(data).upper() == "Y" or str(data) == "예"):
            self.userDict[chatId]["lastAction"] = 12
            username = self.userDict[chatId]["userInfo"]["korailId"]
            password = self.userDict[chatId]["userInfo"]["korailPw"]
            depDate = self.userDict[chatId]["trainInfo"]["depDate"]
            srcLocate = self.userDict[chatId]["trainInfo"]["srcLocate"]
            dstLocate = self.userDict[chatId]["trainInfo"]["dstLocate"]
            depTime = self.userDict[chatId]["trainInfo"]["depTime"]
            trainType = self.userDict[chatId]["trainInfo"]["trainType"]
            maxDepTime = self.userDict[chatId]["trainInfo"]["maxDepTime"]
            specialInfo = self.userDict[chatId]["trainInfo"]["specialInfo"]

            argument = f"{username} {password} {depDate} {srcLocate} {dstLocate} {depTime}00 {trainType} {specialInfo} {chatId} {maxDepTime}"
            print(argument)
            proc = subprocess.Popen(['python', '-m', 'telegramBot.telebotBackProcess', argument], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print (proc.pid)
            self.userDict[chatId]['pid'] = proc.pid
            self.runningStatus[chatId] = {
                "pid": proc.pid,
                "korailId": self.userDict[chatId]['userInfo']['korailId']
            }
            msg = """
예약 프로그램 동작이 시작되었습니다.
매진된 자리에 공석이 생길 때 까지 근삼봇이 열심히 찾아볼게요!
예약에 성공하면 여기로 다시 알려줄게요!
"""       
        elif (str(data).upper() == "N" or str(data) == "아니오"):
            self.manageProgress(chatId, 0)
            msg = "예약 작업이 취소되었습다."
        else:
            msg = """
입력하신 값이 선택지에 없습니다.
'Y'또는 '예'를 입력하시면 예약을 시작합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
"""
        self.sendMessage(chatId, msg)
        return None
    
    def alreadyDoing(self, chatId):
        depDate = self.userDict[chatId]["trainInfo"]["depDate"]
        srcLocate = self.userDict[chatId]["trainInfo"]["srcLocate"]
        dstLocate = self.userDict[chatId]["trainInfo"]["dstLocate"]
        depTime = self.userDict[chatId]["trainInfo"]["depTime"]
        trainTypeShow = self.userDict[chatId]["trainInfo"]["trainTypeShow"]
        specialInfoShow = self.userDict[chatId]["trainInfo"]["specialInfoShow"]
        msg = f"""
현재 예매가 이미 진행중입니다.
===================
출발일 : {depDate}
출발역 : {srcLocate}
도착역 : {dstLocate}
검색기준시각 : {depTime}
열차타입 : {trainTypeShow}
특실여부 : {specialInfoShow}
===================

진행중인 예매를 취소하고 싶으시면 /cancel 을 입력해주세요.
"""
        self.sendMessage(chatId, msg)
    
    def cancelFunc(self, chatId):
        userPid = self.userDict[chatId]["pid"]
        if userPid != 9999999:
            os.kill(userPid, signal.SIGTERM)
            print (f'실행중인 프로세스 {userPid}를 종료합니다.')

            del self.runningStatus[chatId]
            msgToSubscribers = f'{self.userDict[chatId]["userInfo"]["korailId"]}의 예약이 종료되었습니다.'
            self.sendToSubscribers(msgToSubscribers)
                
        self.manageProgress(chatId, 0)
        msg = "예약이 취소되었습니다."
        self.sendMessage(chatId, msg)
        
        return None
    
    
    ## korail class 내부 callback용 함수
    def get(self):
        paramList = set(["chatId", "msg", "status"])
        getParams = set(dict(request.args).keys())
        if (getParams & paramList != paramList):
            return make_response("OK")
        else:
            chatId = request.args.get('chatId')
            msg = request.args.get('msg')
            status = request.args.get('status')
            chatId = int(chatId)
            if (str(status) == "0"):
                print ("예약 완료되어 상태 0으로 초기화")
                self.manageProgress(chatId, 0)
            self.sendMessage(chatId, msg)

            del self.runningStatus[chatId]
            msgToSubscribers = f'{self.userDict[chatId]["userInfo"]["korailId"]}의 예약이 종료되었습니다.'
            self.sendToSubscribers(msgToSubscribers)
        return make_response("OK")
        
    def subscribe(self, chatId):
        self.subscribes.append(chatId)
        data = "열차 이용정보 구독 설정이 완료되었습니다."
        self.sendMessage(chatId, data)

    def sendToSubscribers(self, data):
        for chatId in self.subscribes:
            self.sendMessage(chatId, data)
               
    def getStatusInfo(self, chatId):
        count = len(self.runningStatus)
        usersKorailIds = [state["korailId"] for state in dict.values(self.runningStatus)]
        data = f"총 {count}개의 예약이 실행중입니다. 이용중인 사용자 : {usersKorailIds}"
        self.sendMessage(chatId, data)

    def cancelAll(self, chatId):
        count = len(self.runningStatus)
        pids = [state["pid"] for state in dict.values(self.runningStatus)]
        usersKorailIds = [state["korailId"] for state in dict.values(self.runningStatus)]
        usersChatId = dict.keys(self.runningStatus)

        for pid in pids:
            os.kill(pid, signal.SIGTERM)
            print (f"프로세스 {pid}가 종료되었습니다.")

        dataForManager = f"총 {count}개의 진행중인 예약을 종료했습니다. 이용중이던 사용자 : {usersKorailIds}"
        self.sendMessage(chatId, dataForManager)

        dataForUser = "관리자에 의해 실행중이던 예약이 강제 종료됩니다. 꼬우면 관리자에게 연락하세요."
        for user in usersChatId:
            self.sendMessage(user, dataForUser)

        self.runningStatus = {}

    def getAllUsers(self, chatId):
        allUsers = [user["userInfo"]["korailId"] for user in dict.values(self.userDict)]
        data = f"총 {len(allUsers)}명의 유저가 있습니다 : {allUsers}"
        self.sendMessage(chatId, data)

    def broadCast(self, getText):
        texts = getText.split('/boradcast ')
        allUsers = dict.keys(self.userDict)
        if (len(texts) > 1):
            for user in allUsers:
                self.sendMessage(user, texts[1])
        else:
            for user in allUsers:
                self.sendMessage(user, "앙 기모띠")

    def returnHelp(self, chatId):
        msg = """
- 예약 시작 : /start
- 구독 시작 : /subscribe
- 예약 상태 확인 : /status
- 전체 취소 : /cancelall
- 전체 유저 확인 : /allusers
- 공지 : /broadcast [메시지]
"""
        self.sendMessage(chatId, msg)