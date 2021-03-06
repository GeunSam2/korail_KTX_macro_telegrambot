from flask import Flask, request, jsonify, make_response
from flask_restful import marshal_with, Resource, reqparse, fields
from .korailReserve import Korail
from .botToken import botToken
from multiprocessing import Process
import requests
import time
import base64
import json
import os

class Index(Resource):
    
    s = requests.session()
    sendUrl = "https://api.telegram.org/bot{}".format(botToken)
    
    #userDict : Use like DB.
    # {
    #   "123123": {
    #     "inProgress": True,
    #     "lastAction": "",
    #     "userInfo": { "korailId": "010-1111-1111", "korailPw": "123123" },
    #     "trainInfo": {"srcLocate":"광명", "dstLocate": "광주송정", "depDate": "20210204"}
    #   }
    # }
    userDict = {}
    
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
        #     8 : findingTicket
        if (action == 0):
            self.userDict[chatId]={
                "inProgress": False,
                "lastAction" : action,
                "userInfo" : {},
                "trainInfo" : {}
            }
        elif (action == 1):
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
            self.inputSpecial(chatId, data)
        elif (action == 8):
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
#         print (json.dumps(request.json, sort_keys=True, indent=4))
        if ("edited_message" in request.json):
            pass
            return make_response("OK")
        try:
            initFlag = False
            getText = request.json['message']['text'].strip()
        except:
            initFlag = True
            getText = "코레일 예약봇입니다.\n시작하시려면 /start 를 입력해주세요."
        chatId = request.json['message']['chat']['id']
        
        inProgress, progressNum = self.getUserProgress(chatId)
        print ("CHATID : {} , TEXT : {}, InProgress : {}, Progress : {}".format(chatId, getText, inProgress, progressNum))
        
        if (getText == "/cancel"):
            self.cancelFunc(chatId)
            return make_response("OK")
        elif (progressNum == 9):
            self.alreadyDoing(chatId)
            return make_response("OK")
        
        if (getText == "/start"):
            self.startFunc(chatId)
        elif (getText == "/testFunc"):
            self.testFunc(chatId)
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
(ex_ 20210124) <- 2021년 1월 24일
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
특실 예약여부를 확인해 주십시오.

=================
[1]. 일반실만 예매 진행
[2]. 특실 포함 예매 진행
=================

1 또는 2 를 입력해 주십시오.
"""

        self.sendMessage(chatId, msg)
        return None
    
    def inputSpecial(self, chatId, data):
        if(str(data) in ["1","2"]):
            self.userDict[chatId]["trainInfo"]["specialInfo"] = data
            self.userDict[chatId]["lastAction"] = 8
            depDate = self.userDict[chatId]["trainInfo"]["depDate"]
            srcLocate = self.userDict[chatId]["trainInfo"]["srcLocate"]
            dstLocate = self.userDict[chatId]["trainInfo"]["dstLocate"]
            specialInfo = self.userDict[chatId]["trainInfo"]["specialInfo"]
            msg = """
모든 정보 입력이 완료되었습니다.
정보를 확인하십시오.
===================
출발일 : {}
출발역 : {}
도착역 : {}
특실여부 : {}
===================

'Y'또는 '예'를 입력하시면 예약을 시작합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
예약 완료에 오랜 시간이 걸릴 수 있습니다.
""".format(depDate, srcLocate, dstLocate, specialInfo)
        else:
            msg = """입력하신 값이 1 혹은 2가 아닙니다. 다시 입력해주세요."""
        self.sendMessage(chatId, msg)
        return None
    
    def startReserve(self, chatId, data):
        if (str(data).upper() == "Y" or str(data) == "예"):
            self.userDict[chatId]["lastAction"] = 9
            username = self.userDict[chatId]["userInfo"]["korailId"]
            password = self.userDict[chatId]["userInfo"]["korailPw"]
            depDate = self.userDict[chatId]["trainInfo"]["depDate"]
            srcLocate = self.userDict[chatId]["trainInfo"]["srcLocate"]
            dstLocate = self.userDict[chatId]["trainInfo"]["dstLocate"]
            specialInfo = self.userDict[chatId]["trainInfo"]["specialInfo"]
#             korail = Korail()
#             korail.login(username, password)
#             korail.setInfo(depDate, srcLocate, dstLocate, specialInfo, chatId)
#             backProc = Process(target=korail.reserve, args=())
#             backProc.start() 
            cmd = "python /source/telegramBot/telebotBackProcess.py {} {} {} {} {} {} {} &".format(username, password, depDate, srcLocate, dstLocate, specialInfo, chatId)
            os.system(cmd)
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
        specialInfo = self.userDict[chatId]["trainInfo"]["specialInfo"]
        msg = """
현재 예매가 이미 진행중입니다.
===================
출발일 : {}
출발역 : {}
도착역 : {}
특실여부 : {}
===================

진행중인 예매를 취소하고 싶으시면 /cancel 을 입력해주세요.
""".format(depDate, srcLocate, dstLocate, specialInfo)
        self.sendMessage(chatId, msg)
    
    def cancelFunc(self, chatId):
        self.manageProgress(chatId, 0)
        msg = "예약이 취소되었습니다."
        self.sendMessage(chatId, msg)
        
        ##이미 시작된 예약을 취소하는 기능은 아직 미구현
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
            if (status == 0):
                self.manageProgress(chatId, 0)
            self.sendMessage(chatId, msg)
        return make_response("OK")
    
    
    ##개발자 편하라고 만든 예약함수
    def testFunc(self, chatId):
        self.userDict[chatId]["inProgress"] = True
        self.userDict[chatId]["lastAction"] = 9
        username = "개발자 ID"
        password = "개발자 비번"
        depDate = "20210214" 
        srcLocate = "광주송정"
        dstLocate = "광명"
        specialInfo = "1" 
        self.userDict[chatId]["trainInfo"]["depDate"] = depDate
        self.userDict[chatId]["trainInfo"]["srcLocate"] = srcLocate
        self.userDict[chatId]["trainInfo"]["dstLocate"] = dstLocate
        self.userDict[chatId]["trainInfo"]["specialInfo"] = specialInfo
        cmd = "python /source/telegramBot/telebotBackProcess.py {} {} {} {} {} {} {} &".format(username, password, depDate, srcLocate, dstLocate, specialInfo, chatId)
        os.system(cmd)
        msg = """
예약 프로그램 동작이 시작되었습니다.
매진된 자리에 공석이 생길 때 까지 근삼봇이 열심히 찾아볼게요!
예약에 성공하면 여기로 다시 알려줄게요!
"""       
        self.sendMessage(chatId, msg)
        return None
        
               
        
