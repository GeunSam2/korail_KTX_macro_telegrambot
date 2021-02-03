import requests
import time
from bs4 import BeautifulSoup as bs

class Korail(object):
    s = requests.session()

    reserveInfo = {}
    reserveInfo['depDate'] = ""
    reserveInfo['depTime'] = ""
    reserveInfo['srcLoate'] = ""
    reserveInfo['dstLocate'] = ""
    reserveInfo['special'] = "1"  #일반석1, 특등석:2
    reserveInfo['reserveSuc'] = False
    
    interval = 0.02 ##sec
    
    loginSuc = False
    txtGoHour = "000000"
    specialVal = ""
    
    
    #출력용 방향 정보 만들기
#     direction = "{} -> {}".format(srcLoate, dstLocate)
    
    def __init__(self):
        self.s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
        self.s.headers["Upgrade-Insecure-Requests"] = "1"
        self.s.headers["Referer"] = "http://www.letskorail.com/"
        self.s.headers["Sec-Fetch-Dest"] = "document"
        self.s.headers["Sec-Fetch-User"] = "?1"
        self.s.headers["Sec-Fetch-Mode"] = "navigate"
        self.s.headers["Sec-Fetch-Site"] = "cross-site"
        self.s.headers["Origin"] = "http://www.letskorail.com"
    
    def checkInfo(self):
        check1 = (self.reserveInfo['depDate'] == "")
        check2 = (self.reserveInfo['srcLoate'] == "")
        check3 = (self.reserveInfo['dstLocate'] == "")
        if (check1 and check2 and check3):
            raise exception("초기값 설정이 안되었습니다. setInfo() 함수를 호출하세요.")
        elif (not self.loginSuc):
            raise exception("초기값 설정이 안되었습니다. login()함수를 호출하세요.")
        
    
    def login(self, username, password):
        loginUrl = "https://www.letskorail.com/korail/com/loginAction.do"
        loginData = {
            "selInputFlg": 4,
            "radIngrDvCd": 2,
            "hidMemberFlg": 1,
            "txtDv": 2,
            "UserId": username,
            "UserPwd": password
        }
        login = self.s.post(loginUrl, data=loginData)
        if (login.status_code != 200):
            raise exception("로그인 실패")
        else:
            self.loginSuc = True
            
    def setInfo(self, depDate, srcLoate, dstLocate, specialVal="N"):
        self.reserveInfo['depDate'] = depDate
        self.reserveInfo['srcLoate'] = srcLoate
        self.reserveInfo['dstLocate'] = dstLocate
        self.specialVal = specialVal #Option Default "N" => Don't reserve Special Seat

    def reserveData(self):
        self.checkInfo()
        
        depDate = self.reserveInfo['depDate']
        depTime = self.reserveInfo['depTime']
        srcLoate = self.reserveInfo['srcLoate']
        dstLocate = self.reserveInfo['dstLocate']
        txtGoHour = self.txtGoHour
        
        data={
            "selGoTrain": "05",
            "radJobId": 1,
            "txtGoStart": srcLoate,
            "txtGoEnd": dstLocate,
            "selGoHour": "00",
            "txtGoHour": txtGoHour,
            "txtGoAbrdDt": depDate,
            "checkStnNm": "Y",
            "chkInitFlg": "Y"
        }
        listUrl = "http://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do"
        req = self.s.post(listUrl, data=data)
        soup = bs(req.text, 'html.parser')
        tds = soup.find_all('table')
        
        #열차정보1 예매, 매진 분기처리에 활용
        tdsData = tds[0].find_all('tr')[1:]
        
        #열차정보2 예매 진행시 관련파라미터로 사용
        scriptItems = tds[0].find_all('script')
        
        #페이지 기준 조회이기 때문에 다음 페이지가 있으면 정보를 더 가져와야 함
        try :
            self.txtGoHour = tds[-1].find_all('a')[-1]["href"].split("'")[3]
        except:
            self.txtGoHour = "000000"
            
        #예매에 필요한 정보, 다음 페이지 값 리턴
        return tdsData, scriptItems, txtGoHour
    
    def reserve(self):
        self.getTickets()
        self.reserveInfo['reserveSuc'] = False
        currentTickets = self.ticketCount
        tdsData, scriptItems, txtGoHour = self.reserveData()
        
        if (len(tdsData) == 0):
            print ("예약가능한 노선이 아닙니다.")
            return self.reserveInfo
        
        #페이지 기준 데이터로 예약 가능 여부 확인 후 예매 트리거
        for count, dumy in enumerate(tdsData):
            
            #예약가능 여부 뽑기
            items = dumy.find_all('td')
            seatSpecial = items[4].img['alt'] ##특등석 예약가능 여부
            seatNormal = items[5].img['alt']  ##일반석 예약가능 여부
            
            #예약 필요 정보 뽑기
            scriptItem = scriptItems[count].string.replace("\r\n","").replace("\t","").replace(" ","").split('"')[1:-1]
            while ',' in scriptItem :
                scriptItem.remove(',')
            depCode, arrCode, depDate, depTime = scriptItem[18], scriptItem[20], scriptItem[0], scriptItem[29]
            self.reserveInfo['depTime'] = depTime
            
            #일반좌석 예매
            if (seatNormal == "예약하기"):
                
                req = self.reserveRequests(depCode, arrCode, depDate, depTime, "1")
                self.getTickets()
                if (self.ticketCount > currentTickets):
                #예약현황 리스트 수 확인해서 성공 여부 체크
                    print ("Nomal Reserved")
                    self.reserveInfo['special'] = 1
                    self.reserveInfo['reserveSuc'] = True
                else :
                    print ("Nomal Reserved Fail")


            #특별좌석 예매
            elif (seatSpecial == "예약하기"):
                if (self.specialVal == "Y") : 
                    
                    req = self.reserveRequests(depCode, arrCode, depDate, depTime, "2")
                    self.getTickets()
                    if (self.ticketCount > currentTickets):
                    #예약현황 리스트 수 확인해서 성공 여부 체크
                        print ("Special Reserved")
                        self.reserveInfo['special'] = 2
                        self.reserveInfo['reserveSuc'] = True
                    else :
                        print ("Special Reserved Fail")
            
            print (self.reserveInfo)
            
            #예매에 성공하지 못하면 계속 시도
            if (not self.reserveInfo['reserveSuc']):
                time.sleep(self.interval)
                self.reserve()
            else :
                return self.reserveInfo

    def reserveRequests(self, depCode, arrCode, depDate, depTime, special):
        # 실질적인 예약 기능
        # reservation server checks referer.
        self.s.headers['Referer'] = 'http://www.letskorail.com/ebizprd/EbizPrdTicketPr21111_i1.do'
        url = 'http://www.letskorail.com/ebizprd/EbizPrdTicketPr12111_i1.do'
        data= {
            # 15: 기본
            # 18: 2층석
            # 19: 유아동반
            # 19: 편한대화(중복?)
            # 21: 휠체어
            # 28: 전동휠체어
            # 29: 교통약자(없어진듯)
            # 30: 레포츠보관함
            # 31: 노트북
            # 32: 자전거거치대
            # XX: 수유실인접
            "txtSeatAttCd4": "015",

            "txtTotPsgCnt": "1", #???????????????머선값이고??
            "txtPsgTpCd1": "1", # ??? - 단체예약, 개인예약 구분이라는데...
            "txtCompaCnt1": "1",  #인원

            # 1101: 개인예약
            # 1102: 예약대기
            # 1103: SEATMAP예약
            "txtJobId": "1101", 

            "txtJrnyCnt": "1", # 환승 횟수 (1이면 편도)
            "txtPsrmClCd1": special,  #일반실1, 특실2
            "txtJrnySqno1": "001", # ???
            "txtJrnyTpCd1": "11",  # 편도
            "txtDptDt1": depDate, #날짜
            "txtDptRsStnCd1": depCode, # 출발역 코드
            "txtDptTm1": depTime,  #출발 시간
            "txtArvRsStnCd1": arrCode, # 도착역 코드
            "txtTrnClsfCd1": "00" # 열차 종류(Train Class Code인듯)
        }    
        req = self.s.post(url, data=data)
        return req
    
    def getTickets(self):
        ticketUrl="https://www.letskorail.com/ebizprd/EbizPrdTicketpr13500W_pr13510.do"
        req = self.s.get(ticketUrl)
        soup = bs(req.text, 'html.parser')
        ticketCountAll = len(soup.find_all('input', {"name": "radPnr", "type": "radio"})) ##마이페이지에 있는 티켓 갯수
        ticketCountYet = 0
        labels = []
        for num in range(ticketCountAll):
            spansSoup = soup.find_all('td', {"class": "txt_red left_black"})[num]
            span = spansSoup.text.strip()
            if ("결제완료" in span):
                pass
                #결제 완료에 대한 추가 기능 생각나면 넣자
            else:
                print ("예약티켓")

                labelSoup = soup.find_all('label', {"for": "radio{}".format(num)})
                ticketCountYet += 1
                labels.append([])
                for label in labelSoup:
                    labels[-1].append(label.text)
                    
        #예매티켓 갯수 갱신 (예매 확인용)
        self.ticketCount = ticketCountYet
        
        #예매티켓에 대한 정보 array로 전달
        return labels