import pandas as pd
import LLMControl as llm
import re

def multiple(a, b):
    c = ''
    a, b = a[::-1], b[::-1]
    a1, b1 = len(a)-1, len(b)-1
    k = 0
    result = 0
    while k <= a1+b1:
        for i in range(max(0, k-b1), min(a1+1, k+1)):
            result += int(a[i])*int(b[k-i])
        c = str(result%10)+c
        result = result//10
        k += 1
    if result != 0:
        c = result+c
    return c

def compare(a, b):
    if len(a) > len(b):
        return True
    elif len(a) < len(b):
        return False
    else:
        for i in range(len(a)):
            if a[i] > b[i]:
                return True
            elif a[i] < b[i]:
                return False
    return True

class company():
    def __init__(self, name, product, compete, develop, num):
        self.name = name
        self.main_product = product
        self.main_compete = compete
        self.develop = develop
        self.number = pd.DataFrame(index=num.index, columns=num.columns)
        for i in num.index:
            if num.loc[i, '本报告期'] == 'No Data':
                continue
            else:
                a = num.loc[i, '本报告期']
                a1 = ''
                for j in a:
                    if j >= '0' and j <= '9' or j == '.' or j == '-':
                        a1 = a1 + j
                self.number.loc[i, '本报告期'] = a1
                try:
                    b = num.loc[i, '上年同期']
                    b1 = ''
                    for j in b:
                        if j>='0' and j<='9' or j == '.' or j == '-':
                            b1 = b1+j
                    self.number.loc[i, '上年同期'] = b1
                    self.number.loc[i, '本报告期比上年同期增减'] = num.loc[i, '本报告期比上年同期增减']
                except:
                    continue

    def number_print(self):
        print(self.number)
        return

    def idea_point(self):
        try:
            idea_cost = int(self.number.at['研发费用', '本报告期'][:-6])
            income = int(self.number.at['营业收入', '本报告期'][:-6])
            idea_percent = idea_cost/income * 100
            point = round(3.0 + idea_percent/1.5, 1)
            if point >= 7.0:
                point = 7.0
        except:
            point = 4.5
        response = llm.AskAI_turbo(self.main_product+"请根据以上信息，返回该公司的创新能力评分。评分标准：创新能力强9.0分左右，普通企业7.0分左右，创新能力不强给5.0分左右。如果是高新技术产业，额外加1分。按照以下格式回答，保留评分两侧的中括号：\n创新能力：[创新能力评分]")
        matches = re.findall(r'\[(.*?)]', response)
        for match in matches:
            try:
                score = float(match)
                return round(score*0.3 + point, 1)
            except:
                continue
        return round(7.0, 1)

    def speed_point(self):
        point = 0.0
        try:
            idea_percent = float(self.number.at['研发费用', '本报告期比上年同期增减'][:-1])
            t = round(1.5 + idea_percent/40, 1)
            if t >= 2.0:
                t = 2.0
            elif t <= 1.0:
                t = 1.0
            point += t
        except:
            point += 1.5
        try:
            all_account_percent = float(self.number.at['营业收入', '本报告期比上年同期增减'][:-1])
            t =round(2.5+all_account_percent/15, 1)
            if t >= 5.0:
                t = 5.0
            elif t <= 0.0:
                t = 0.0
            point += t
        except:
            point += 2.5
        try:
            profit_percent = float(self.number.at['加权平均净资产收益率', '本报告期比上年同期增减'][:-1])
            t = round(1.5 + profit_percent/2, 1)
            if t >= 3.0:
                t = 3.0
            elif t <= 0.0:
                t = 0.0
            point += t
        except:
            point += 1.5
        return round(point, 1)

    def ensure_point(self):
        point = 9.5
        try:
            all_account = self.number.at['总资产', '本报告期'][:-3]
        except:
            try:
                all_account = multiple(self.number.at['营业收入', '本报告期'][:-3], '3')
            except:
                try:
                    all_account = multiple(self.number.at['归属于上市公司股东的净资产', '本报告期'][:-3], '15')[:-1]
                except:
                    return 6.5
        try:
            operate_account = self.number.at['经营活动产生的现金流量净额', '本报告期'][:-3]
            if operate_account[0] == '-':
                operate_account = operate_account[1:]
                if compare(multiple(operate_account, '2'), all_account):
                    point -= 6.0
                elif compare(multiple(operate_account, '3'), all_account):
                    point -= 3.0
                elif compare(multiple(operate_account, '5'), all_account):
                    point -= 2.0
                elif compare(multiple(operate_account, '10'), all_account):
                    point -= 1.0
                else:
                    point -= 0.5
        except:
            point -= 0.5
        try:
            non_operate_account = self.number.at['非经营性损益合计', '本报告期']
            if non_operate_account[0] == '-':
                non_operate_account = non_operate_account[1:]
                if compare(multiple(non_operate_account, '2'), all_account):
                    point -= 6.0
                elif compare(multiple(non_operate_account, '3'), all_account):
                    point -= 3.0
                elif compare(multiple(non_operate_account, '5'), all_account):
                    point -= 2.0
                elif compare(multiple(non_operate_account, '10'), all_account):
                    point -= 1.0
                else:
                    point -= 0.5
        except:
            point -= 0.5
        try:
            all_account_percent = float(self.number.at['总资产', '本报告期比上年同期增减'][:-1])
            if all_account_percent<0:
                if all_account_percent < -16:
                    point += all_account_percent/4
                elif all_account_percent < -6:
                    t = all_account_percent/3
                    if t <= -4:
                        t = -4
                else:
                    t = all_account_percent/2
                    if t <= -2:
                        t = -2
            point += t
        except:
            point -= 0.5
        if point <= 0.0:
            point = 0.0
        return round(point, 1)

    def compete_point(self):
        response = llm.AskAI_turbo(self.main_compete+"\n请根据以上信息，返回该公司的竞争力评分。评分标准：行业头部企业9.0分左右，行业普通中型企业7.0分左右，行业竞争力不强给5.0分左右。按照以下格式回答，保留评分两侧的中括号：\n竞争力：[竞争力评分]")
        matches = re.findall(r'\[(.*?)]', response)
        for match in matches:
            try:
                score = float(match)
                return round(score, 1)
            except:
                continue
        return round(7.0, 1)

    def profit_point(self):
        point = 0.0
        try:
            per_profit = float(self.number.at['稀释每股收益', '本报告期'])
            point += 2.5+round((per_profit-0.5)*2, 1)
        except:
            try:
                per_profit = float(self.number.at['基本每股收益', '本报告期'])
                point += 2.5 + round((per_profit - 0.5) * 2, 1)
            except:
                point += 2.5
        if point >= 5.0:
            point = 5.0
        elif point <= 0.0:
            point = 0.0
        try:
            per_profit = float(self.number.at['加权平均净资产收益率', '本报告期'][:-1])
            t = 3.0+round((per_profit-5)/6, 1)
            if t >= 5.0:
                t = 5.0
            elif t <= 1.0:
                t = 1.0
        except:
            t = 3.0
        point += t
        return round(point, 1)

def get_scores(enter):
    enter = pd.DataFrame(enter)
    weight = pd.array([0.15, 0.2, 0.25, 0.1, 0.3])
    name = enter.at[0, '本报告期']
    enter.drop(index=0, inplace=True)
    enter.drop(index=1, inplace=True)
    enter.index = enter.项目
    enter.drop(columns=['项目'], inplace=True)
    product = enter.at['主营业务和发展规划', '本报告期']
    compete = enter.at['主营业务和发展规划', '上年同期']
    develop = enter.at['主营业务和发展规划', '本报告期比上年同期增减']
    enter.drop(index=['主营业务和发展规划'], inplace=True)
    a1 = company(name, product, compete, develop, enter)

    point = pd.array([a1.idea_point(), a1.speed_point(), a1.ensure_point(), a1.compete_point(), a1.profit_point()])
    point_aver = round(sum(point * weight), 1)

    result_scores = {
        '综合评分':point_aver,
        '创新能力':point[0],
        '发展速度':point[1],
        '风险控制':point[2],
        '竞争力':point[3],
        '盈利能力':point[4]
    }

    print('创新能力', point[0])
    print('发展速度', point[1])
    print('抗风险能力', point[2])
    print('市场竞争力', point[3])
    print('收益情况', point[4])
    print(point_aver)

    return result_scores

if __name__ == "__main__":
    data = pd.read_csv('data2.csv')
    get_scores(data)
