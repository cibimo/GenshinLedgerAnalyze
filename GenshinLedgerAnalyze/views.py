from django.http.response import *
from django.shortcuts import render, redirect
import os, json, requests, base64, datetime

def base64Encode(enstr):
    return base64.b64encode(enstr.encode()).decode()

def base64Decode(enstr):
    return base64.b64decode(enstr).decode()

def addMonth(srcDate):
    return srcDate.replace(year=srcDate.year+1, month=1) if srcDate.month == 12 else srcDate.replace(month=srcDate.month+1)

def getUserInfo():
    if os.path.exists("userInfo.json"):
        return json.loads(open("userInfo.json").read())

def addMonth(srcDate):
    return srcDate.replace(year=srcDate.year + 1, month=1) if srcDate.month == 12 else srcDate.replace(
        month=srcDate.month + 1)

def getUserInfo():
    if os.path.exists("userInfo.json"):
        return json.loads(open("userInfo.json").read())


class YS:
    def __init__(self, ledgerType):
        self.ledgerType = ledgerType  # 1:原石 2:摩拉
        self.userInfo = getUserInfo()

    def getYSLedger(self, month, page, limit=100):
        return requests.get("https://hk4e-api.mihoyo.com/event/ys_ledger/monthDetail", params={
            'page': page,
            'month': month,
            'limit': limit,
            'type': self.ledgerType,
            'bind_uid': self.userInfo['uid'],
            'bind_region': self.userInfo['region'],
        }, headers={'cookie': self.userInfo['cookie']}).json()

    def readYSLedgerFromLocal(self, year, month):
        if os.path.exists(
                f"{self.userInfo['uid']}/{self.ledgerType}/YSLedger_{year}{str(month) if len(str(month)) == 2 else f'0{str(month)}'}.json"):
            return json.loads(open(
                f"{self.userInfo['uid']}/{self.ledgerType}/YSLedger_{year}{str(month) if len(str(month)) == 2 else f'0{str(month)}'}.json").read())

    def writeYSLedgerToLocal(self, year, month, YSLedger):
        if not os.path.exists(f"{self.userInfo['uid']}"):
            os.mkdir(f"{self.userInfo['uid']}")
        if not os.path.exists(f"{self.userInfo['uid']}/{self.ledgerType}"):
            os.mkdir(f"{self.userInfo['uid']}/{self.ledgerType}")

        f = open(
            f"{self.userInfo['uid']}/{self.ledgerType}/YSLedger_{year}{str(month) if len(str(month)) == 2 else f'0{str(month)}'}.json",
            'w+')
        f.write(json.dumps(YSLedger, ensure_ascii=False, separators=(',', ':')))
        f.close()

    def getYSLedgerByMonth(self, month):
        monthLedger = []
        page = 1
        haveLedger = True
        while haveLedger:
            rsp_json = self.getYSLedger(month, page)
            monthLedger += rsp_json['data']['list']
            haveLedger = True if rsp_json['data']['list'] else False
            page += 1
        return monthLedger

    def saveYSLedgerByMonth(self, month):
        nowTime = datetime.datetime.now()
        monthLedger = self.getYSLedgerByMonth(month)

        monthLedger = {'updateTime': nowTime.strftime('%Y-%m-%d %H:%M:%S'), 'ledger': monthLedger}
        self.writeYSLedgerToLocal(nowTime.year, month, monthLedger)

    def updateAllLedger(self):
        nowTime = datetime.datetime.now()
        for i in self.getYSLedger(nowTime.strftime('%m'), 1, 20)['data']['optional_month']:
            localData = self.readYSLedgerFromLocal(nowTime.year, i)
            if (not localData) or (
                    datetime.datetime.strptime(localData['updateTime'], '%Y-%m-%d %H:%M:%S').month <= int(i)):
                self.saveYSLedgerByMonth(i)

    def getLedgerFileList(self):
        localFilelist = []
        if not os.path.exists(f"{self.userInfo['uid']}/{self.ledgerType}"):
            return []
        for i in os.listdir(f"{self.userInfo['uid']}/{self.ledgerType}"):
            if i.startswith('YSLedger_') and i.endswith('.json'):
                localFilelist.append(i)
        return sorted(localFilelist, key=lambda x: int(x[9:15]))

    def getLedgerList(self):
        ledgerFilelist = self.getLedgerFileList()
        ledgerList = []
        for i in ledgerFilelist:
            ledgerList += json.loads(open(f"{self.userInfo['uid']}/{self.ledgerType}/{i}").read())['ledger'][::-1]
        return ledgerList

    def getConfig(self):
        ledgerList = self.getLedgerList()

        actionList = []
        for i in ledgerList:
            if i['action'] not in actionList:
                actionList.append(i['action'])

        analyzeList = {}

        rawStartDay, rawEndDay = datetime.datetime.strptime(ledgerList[0]['time'].split(' ')[0],
                                                            '%Y-%m-%d'), datetime.datetime.strptime(
            ledgerList[-1]['time'].split(' ')[0], '%Y-%m-%d')

        dateList = []
        startDay, endDay = rawStartDay, rawEndDay
        while startDay <= endDay:
            dateList.append(startDay.strftime('%Y-%m-%d'))
            startDay += datetime.timedelta(days=1)

        for i in actionList:
            startDay, endDay = rawStartDay, rawEndDay
            analyzeList[i] = []
            while startDay <= endDay:
                YStmp = 0
                for m in ledgerList:
                    if m['action'] == i and datetime.datetime.strptime(m['time'],
                                                                       '%Y-%m-%d %H:%M:%S') >= startDay + datetime.timedelta(
                            hours=4) and datetime.datetime.strptime(m['time'],
                                                                    '%Y-%m-%d %H:%M:%S') < startDay + datetime.timedelta(
                            hours=28):
                        YStmp += m['num']
                analyzeList[i].append(YStmp)
                startDay += datetime.timedelta(days=1)

        option = {
            "title": {
                "text": "原石获取来源统计分析（无充值来源）" if str(self.ledgerType) == '1' else "摩拉获取来源统计分析",
                "x": "center"
            },
            "series": [
                {
                    "name": i,
                    "type": "bar",
                    "stack": "YS",
                    "emphasis": {
                        "focus": "series"
                    },
                    "data": analyzeList[i]
                } for i in analyzeList
            ],
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {
                    "type": "shadow"
                }
            },
            "dataZoom": [
                {
                    "type": "slider",
                },
                {
                    "type": "inside"
                }
            ],
            "legend": {
                "top": "3%",
                "left": "center"
            },
            'color': ['#37A2DA', '#32C5E9', '#67E0E3', '#9FE6B8', '#FFDB5C', '#ff9f7f', '#fb7293', '#E062AE', '#E690D1',
                      '#e7bcf3', '#9d96f5', '#8378EA', '#96BFFF'],
            "grid": {
                "left": "5%",
                "right": "5%",
                "bottom": "10%",
                "containLabel": True
            },
            "xAxis": [
                {
                    "type": "category",
                    "data": dateList
                }
            ],
            "yAxis": [
                {
                    "type": "value"
                }
            ]
        }

        return option

    def getMonthViewConfig(self, ledgerType):
        ledgerFileList = self.getLedgerFileList()
        if not ledgerFileList:
            return
        xList, yList = [], []
        for i in ledgerFileList:
            xList.append(f"{i[9: 13]}-{i[13: 15]}")
            valueTotal = 0
            for m in json.loads(open(f"{self.userInfo['uid']}/{self.ledgerType}/{i}").read())['ledger']:
                valueTotal += m['num']
            yList.append(valueTotal)
        return {
            "title": {},
            "series": [
                {
                    "type": "line",
                    "smooth": True,
                    "data": yList,
                    "label": {
                        "show": True,
                        "position": 'top'
                    }
                }
            ],
            "xAxis": [
                {
                    "type": "category",
                    "data": xList
                }
            ],
            "yAxis": [
                {
                    "type": "value"
                }
            ]
        }

def setUser(request):
    with open("userInfo.json", "w+") as f:
        f.write(json.dumps({
            'uid':request.GET.get('uid'),
            'cookie':base64Decode(request.GET.get('cookie')),
            'nickname':request.GET.get('nickname'),
            'region': request.GET.get('region'),
            'level': request.GET.get('level')
        }))
    return render(request, "info.html", {"title": "设置成功", "text": "请点击按钮回到主页", "redirect": "/home"})

def getUserInfoByCookie(cookie):
    return requests.get("https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn", headers={"Cookie":cookie}).json()['data']['list']

def home(request):
    userInfo = getUserInfo()
    if not userInfo:
        return render(request, "info.html", {"title": "请先设置Cookie信息", "text": "点击按钮进行设置", "redirect": "/setCookie"})
    option1 = YS(1).getMonthViewConfig(1)
    option2 = YS(2).getMonthViewConfig(2)
    return render(request, "home.html", {'userInfo': userInfo, 'text1':'' if option1 else '暂无概览信息', 'text2':'' if option2 else '暂无概览信息', 'option1': json.dumps(option1, ensure_ascii=False, separators=(',',':')), 'option2': json.dumps(option2, ensure_ascii=False, separators=(',',':'))})

def setCookie(request):
    if request.method == "GET":
        return render(request, "setCookie.html")
    elif request.method == "POST":
        cookie = request.POST.get("cookie","")
        if not cookie:
            return render(request, "info.html", {"title": "运行异常", "text": "Cookie为空", "redirect": "/setCookie"})
        try:
            return render(request, "selectUser.html", {"userList": getUserInfoByCookie(cookie), "cookie": base64Encode(cookie)})
        except:
            return render(request, "info.html", {"title": "运行异常", "text": "请检查Cookie是否有效", "redirect": "/setCookie"})

def analyze(request):
    analyzeType = request.GET.get("type")
    ys = YS(analyzeType)
    if int(request.GET.get("fresh",0)) == 1:
        ys.updateAllLedger()
        return redirect(f"/analyze?type={analyzeType}")
    if not ys.getLedgerFileList():
        ys.updateAllLedger()
    option = ys.getConfig()
    return render(request, "analyze.html", {"option": json.dumps(option, ensure_ascii=False, separators=(',',':')), "type": analyzeType})