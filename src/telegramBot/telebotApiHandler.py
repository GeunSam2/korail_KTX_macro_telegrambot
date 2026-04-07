from korail2 import ReserveOption, TrainType
from flask import request, make_response
from flask_restful import Resource
from datetime import datetime
from .korailReserve import Korail
from .messages import Messages, MessageService
import requests
import os
import subprocess
import signal

class Index(Resource):

    s = requests.session()
    BOTTOKEN = os.environ.get('BOTTOKEN')
    sendUrl = "https://api.telegram.org/bot{}".format(BOTTOKEN)

    # 메시지 서비스 초기화
    msg_service = MessageService(s, sendUrl)
    
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

    #Payment completion status : Track payment reminder status
    # {
    #     123123: True/False  # True if user confirmed payment
    # }
    paymentCompleted = {}

    #Admin authentication status : Track admin authentication
    # {
    #     123123: {
    #         "authenticated": True/False,
    #         "pending_command": "/subscribe"  # 인증 후 실행할 명령어
    #     }
    # }
    adminAuth = {}

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
            if (chatId in self.userDict):
                self.userDict[chatId]["inProgress"] = False
                self.userDict[chatId]["lastAction"] = 0
                self.userDict[chatId]["trainInfo"] = {}
                self.userDict[chatId]["pid"] = 9999999
            else:
                self.userDict[chatId]={
                    "inProgress": False,
                    "lastAction" : 0,
                    "userInfo" : {
                        "korailId": "no-login-yet",
                        "korailPw": "no-login-yet"
                    },
                    "trainInfo" : {},
                    "pid": 9999999
                }
            return

        if (len(self.runningStatus) > 0 and chatId not in dict.keys(self.runningStatus)):
            self.msg_service.send(chatId, Messages.ERROR_BUSY)
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
            self.msg_service.send(chatId, Messages.ERROR_GENERIC)
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
            getText = Messages.INIT
        chatId = request.json['message']['chat']['id']
        chatId = int(chatId)
        
        inProgress, progressNum = self.getUserProgress(chatId)
        print ("CHATID : {} , TEXT : {}, InProgress : {}, Progress : {}".format(chatId, getText, inProgress, progressNum))
        
        if (getText == "/cancel"):
            self.cancelFunc(chatId)
            return make_response("OK")

        # 결제 완료 확인 - 예약 리마인더가 진행 중인 경우 아무 메시지나 입력하면 중단
        if chatId in self.paymentCompleted and not self.paymentCompleted[chatId]:
            # 리마인더 진행 중이고 아직 결제 확인 안된 상태
            if getText and getText[0] != '/':  # 일반 메시지 입력 시
                self.confirmPayment(chatId)
                return make_response("OK")

        # 관리자 인증 대기 중인 경우
        if chatId in self.adminAuth and self.adminAuth[chatId].get("pending_command"):
            self.handleAdminAuth(chatId, getText)
            return make_response("OK")

        if (getText == "/결제완료" or getText == "/paymentdone"):
            self.confirmPayment(chatId)
        elif (getText == "/subscribe"):
            self.requireAdminAuth(chatId, "/subscribe")
        elif (getText == "/status"):
            self.getStatusInfo(chatId)
        elif (getText == "/cancelall"):
            self.requireAdminAuth(chatId, "/cancelall")
        elif (getText == "/allusers"):
            self.requireAdminAuth(chatId, "/allusers")
        elif (getText.split(' ')[0] == '/broadcast'):
            self.requireAdminAuth(chatId, getText)
        elif (getText == "/help"):
            self.returnHelp(chatId)
        elif (progressNum == 12):
            self.alreadyDoing(chatId)
            return make_response("OK")
        elif (getText == "/start"):
            self.startFunc(chatId)
        elif (getText[0] == "/"):
            self.msg_service.send(chatId, Messages.ERROR_INVALID_COMMAND)
        else :
            if (inProgress):
                self.manageProgress(chatId, progressNum, getText)
            else:
                if (initFlag):
                    self.msg_service.send(chatId, getText)
                else :
                    self.msg_service.send(chatId, Messages.ERROR_NO_PROGRESS)
        return make_response("OK")
    
    
    ##사용자에게 메시지 보내기 (레거시 호환용)
    def sendMessage(self, chatId, getText):
        self.msg_service.send(chatId, getText)
        return None
    
    def startFunc(self, chatId):
        self.userDict[chatId]["inProgress"] = True
        self.userDict[chatId]["lastAction"] = 1
        self.msg_service.send(chatId, Messages.WELCOME)
        return None
    
    def startAccept(self, chatId, data="Y"):
        if (str(data).upper() == "Y" or str(data) == "예"):
            self.userDict[chatId]["lastAction"] = 2
            msg = Messages.REQUEST_PHONE
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
                    msg = Messages.LOGIN_SUCCESS
                    self.userDict[chatId]["lastAction"] = 4
                else:
                    self.manageProgress(chatId, 0)
                    msg = Messages.ERROR_ADMIN_LOGIN
            else:
                self.manageProgress(chatId, 0)
                msg = Messages.ERROR_ADMIN_ENV
        else:
            self.manageProgress(chatId, 0)
            msg = Messages.CANCELLED_BY_USER
        self.msg_service.send(chatId, msg)
        return None
    
    #아이디 입력 함수
    def inputId(self, chatId, data):
        allowList = os.environ.get('ALLOW_LIST', '')
        if ("-" not in data):
            msg = Messages.ERROR_PHONE_FORMAT
        elif (data not in allowList):
            msgToSubscribers = Messages.subscriber_not_allowed(data)
            self.sendToSubscribers(msgToSubscribers)
            self.manageProgress(chatId, 0)
            msg = Messages.ERROR_NOT_SUBSCRIBER
        else:
            self.userDict[chatId]["userInfo"]["korailId"] = data
            self.userDict[chatId]["lastAction"] = 3
            msg = Messages.REQUEST_PASSWORD
        self.msg_service.send(chatId, msg)
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
            self.userDict[chatId]["lastAction"] = 4
            self.msg_service.send(chatId, Messages.LOGIN_SUCCESS)
        else:
            if (str(data).upper() == "Y" or str(data) == "예"):
                self.startAccept(chatId)
            elif (str(data).upper() == "N" or str(data) == "아니오"):
                self.manageProgress(chatId, 0)
                self.msg_service.send(chatId, Messages.CANCELLED)
            else:
                self.msg_service.send(chatId, Messages.LOGIN_FAILED_RETRY.format(username=username))

        return None
    
    #출발일 입력 함수
    def inputDate(self, chatId, data):
        today = datetime.today().strftime("%Y%m%d")
        if (str(data).isdigit() and len(str(data)) == 8 and data >= today):
            self.userDict[chatId]["trainInfo"]["depDate"] = data
            self.userDict[chatId]["lastAction"] = 5
            msg = Messages.REQUEST_DATE
        else:
            msg = Messages.ERROR_DATE_FORMAT
        self.msg_service.send(chatId, msg)
        return None
        
    def inputSrcLoate(self, chatId, data):
        self.userDict[chatId]["trainInfo"]["srcLocate"] = data
        self.userDict[chatId]["lastAction"] = 6
        self.msg_service.send(chatId, Messages.REQUEST_SRC_STATION)
        return None

    def inputDstLoate(self, chatId, data):
        self.userDict[chatId]["trainInfo"]["dstLocate"] = data
        self.userDict[chatId]["lastAction"] = 7
        self.msg_service.send(chatId, Messages.REQUEST_DST_STATION)
        return None


    def inputDepTime(self, chatId, data):
        if (len(str(data)) == 4 and str(data).isdecimal()):
            self.userDict[chatId]["trainInfo"]["depTime"] = data
            self.userDict[chatId]["lastAction"] = 8
            msg = Messages.REQUEST_DEP_TIME
        else:
            msg = Messages.ERROR_TIME_FORMAT

        self.msg_service.send(chatId, msg)
        return None

    def inputMaxDepTime(self, chatId, data):
        if (len(str(data)) == 4 and str(data).isdecimal()):
            self.userDict[chatId]["trainInfo"]["maxDepTime"] = data
            self.userDict[chatId]["lastAction"] = 9
            msg = Messages.REQUEST_TRAIN_TYPE
        else:
            msg = Messages.ERROR_TIME_FORMAT

        self.msg_service.send(chatId, msg)
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
            msg = Messages.REQUEST_SEAT_TYPE
        else:
            msg = Messages.ERROR_TRAIN_TYPE_INVALID
        self.msg_service.send(chatId, msg)
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

            msg = Messages.CONFIRM_RESERVATION.format(
                depDate=self.userDict[chatId]["trainInfo"]["depDate"],
                srcLocate=self.userDict[chatId]["trainInfo"]["srcLocate"],
                dstLocate=self.userDict[chatId]["trainInfo"]["dstLocate"],
                depTime=self.userDict[chatId]["trainInfo"]["depTime"],
                maxDepTime=self.userDict[chatId]["trainInfo"]["maxDepTime"],
                trainTypeShow=self.userDict[chatId]["trainInfo"]["trainTypeShow"],
                specialInfoShow=specialInfoShow
            )
        else:
            msg = Messages.ERROR_SEAT_TYPE_INVALID
        self.msg_service.send(chatId, msg)
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

            arguments = [username, password, depDate, 
                        srcLocate, dstLocate, f'{depTime}00', 
                        trainType, specialInfo, chatId, maxDepTime]
            arguments = [str(argument) for argument in arguments]
            print(arguments)
            cmd = ['python', '-m', 'telegramBot.telebotBackProcess'] + arguments
            proc = subprocess.Popen(cmd)
            self.userDict[chatId]['pid'] = proc.pid
            self.runningStatus[chatId] = {
                "pid": proc.pid,
                "korailId": self.userDict[chatId]['userInfo']['korailId']
            }

            msgToSubscribers = Messages.subscriber_started(username, srcLocate, dstLocate, depDate)
            self.sendToSubscribers(msgToSubscribers)

            msg = Messages.RESERVATION_STARTED
        elif (str(data).upper() == "N" or str(data) == "아니오"):
            self.manageProgress(chatId, 0)
            msg = Messages.CANCELLED_TYPO
        else:
            msg = Messages.ERROR_CONFIRM_INVALID
        self.msg_service.send(chatId, msg)
        return None
    
    def alreadyDoing(self, chatId):
        msg = Messages.ALREADY_RUNNING.format(
            depDate=self.userDict[chatId]["trainInfo"]["depDate"],
            srcLocate=self.userDict[chatId]["trainInfo"]["srcLocate"],
            dstLocate=self.userDict[chatId]["trainInfo"]["dstLocate"],
            depTime=self.userDict[chatId]["trainInfo"]["depTime"],
            trainTypeShow=self.userDict[chatId]["trainInfo"]["trainTypeShow"],
            specialInfoShow=self.userDict[chatId]["trainInfo"]["specialInfoShow"]
        )
        self.msg_service.send(chatId, msg)
    
    def cancelFunc(self, chatId):
        userPid = self.userDict[chatId]["pid"]
        if userPid != 9999999:
            os.kill(userPid, signal.SIGTERM)
            print (f'실행중인 프로세스 {userPid}를 종료합니다.')

            del self.runningStatus[chatId]
            msgToSubscribers = Messages.subscriber_ended(self.userDict[chatId]["userInfo"]["korailId"])
            self.sendToSubscribers(msgToSubscribers)

        self.manageProgress(chatId, 0)
        self.msg_service.send(chatId, Messages.CANCELLED)

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
                # 리마인더 시작을 위해 결제 완료 상태 False로 초기화
                self.paymentCompleted[chatId] = False
            self.msg_service.send(chatId, msg)

            del self.runningStatus[chatId]
            msgToSubscribers = Messages.subscriber_ended(self.userDict[chatId]["userInfo"]["korailId"])
            self.sendToSubscribers(msgToSubscribers)
        return make_response("OK")
        
    def subscribe(self, chatId):
        if (chatId not in self.subscribes):
            self.subscribes.append(chatId)
            data = Messages.SUBSCRIBE_SUCCESS
        else:
            data = Messages.SUBSCRIBE_ALREADY
        self.msg_service.send(chatId, data)

    def sendToSubscribers(self, data):
        self.msg_service.send_to_multiple(self.subscribes, data)
               
    def getStatusInfo(self, chatId):
        count = len(self.runningStatus)
        usersKorailIds = [state["korailId"] for state in dict.values(self.runningStatus)]
        data = Messages.status_info(count, usersKorailIds)
        self.msg_service.send(chatId, data)

    def cancelAll(self, chatId):
        count = len(self.runningStatus)
        pids = [state["pid"] for state in dict.values(self.runningStatus)]
        usersKorailIds = [state["korailId"] for state in dict.values(self.runningStatus)]
        usersChatId = dict.keys(self.runningStatus)

        for pid in pids:
            os.kill(pid, signal.SIGTERM)
            print (f"프로세스 {pid}가 종료되었습니다.")

        dataForManager = Messages.admin_cancelled_all(count, usersKorailIds)
        self.msg_service.send(chatId, dataForManager)

        self.msg_service.send_to_multiple(usersChatId, Messages.ADMIN_FORCE_CANCEL)
        for user in usersChatId:
            self.manageProgress(user, 0)

        self.runningStatus = {}

    def getAllUsers(self, chatId):
        allUsers = [user["userInfo"]["korailId"] for user in dict.values(self.userDict)]
        data = Messages.all_users_info(len(allUsers), allUsers)
        self.msg_service.send(chatId, data)

    def broadCast(self, getText):
        texts = getText.split('/broadcast ')
        allUsers = dict.keys(self.userDict)
        if (len(texts) > 1):
            self.msg_service.send_to_multiple(allUsers, texts[1])
        else:
            self.msg_service.send_to_multiple(allUsers, Messages.ADMIN_BROADCAST_DEFAULT)

    def returnHelp(self, chatId):
        self.msg_service.send(chatId, Messages.HELP)

    def confirmPayment(self, chatId):
        """사용자가 결제 완료를 확인"""
        self.paymentCompleted[chatId] = True
        self.msg_service.send(chatId, Messages.PAYMENT_CONFIRMED)

    def requireAdminAuth(self, chatId, command):
        """관리자 인증 요청"""
        # 이미 인증된 상태인지 확인
        if chatId in self.adminAuth and self.adminAuth[chatId].get("authenticated"):
            # 인증된 경우 바로 명령 실행
            self.executeAdminCommand(chatId, command)
        else:
            # 인증 필요
            self.adminAuth[chatId] = {
                "authenticated": False,
                "pending_command": command
            }
            self.msg_service.send(chatId, Messages.ADMIN_AUTH_REQUIRED)

    def handleAdminAuth(self, chatId, password):
        """관리자 비밀번호 확인 및 명령 실행"""
        admin_password = os.environ.get("USERPW")

        if password == admin_password:
            # 인증 성공
            self.adminAuth[chatId]["authenticated"] = True
            pending_command = self.adminAuth[chatId]["pending_command"]
            self.adminAuth[chatId]["pending_command"] = None

            self.msg_service.send(chatId, Messages.ADMIN_AUTH_SUCCESS)
            self.executeAdminCommand(chatId, pending_command)
        else:
            # 인증 실패
            self.adminAuth[chatId]["pending_command"] = None
            self.msg_service.send(chatId, Messages.ADMIN_AUTH_FAILED)

    def executeAdminCommand(self, chatId, command):
        """관리자 명령 실행"""
        if command == "/subscribe":
            self.subscribe(chatId)
        elif command == "/cancelall":
            self.cancelAll(chatId)
        elif command == "/allusers":
            self.getAllUsers(chatId)
        elif command and command.startswith('/broadcast'):
            self.broadCast(command)


class CheckPayment(Resource):
    """결제 완료 상태 확인 API 엔드포인트"""

    def get(self):
        chatId = request.args.get('chatId')
        if not chatId:
            return {'completed': False}

        try:
            chatId = int(chatId)
            # Index 클래스의 paymentCompleted 딕셔너리 참조
            completed = Index.paymentCompleted.get(chatId, False)
            return {'completed': completed}
        except:
            return {'completed': False}