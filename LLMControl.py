from dashscope import Generation
import dashscope
from http import HTTPStatus
import random
import re
import datetime

import DataControl as data_ctrl
#from FrontEnd import Overall_Brief_Info_List

Dashscope_api_key = "YOUR_DASHSCOPE_API_KEY"
Model_Choice = "qwen-max"


def AskAI_turbo(content):
    dashscope.api_key = Dashscope_api_key
    messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': content}]
    response = Generation.call(model="qwen-max",
                               messages = messages,
                               # 设置随机数种子seed，如果没有设置，则随机数种子默认为1234
                               seed = random.randint(1, 10000),
                               temperature=0.4,
                               top_p=0.8,
                               top_k=50,
                               # 将输出设置为"message"格式
                               result_format='message')
    if response.status_code == HTTPStatus.OK:
        response_str = response["output"]["choices"][0]["message"]["content"]
        response_str = re.sub(r'\n{2,}', '\n', response_str)
        print("大模型答复：")
        print(response_str)
        return response_str
    else:
        print("大模型反馈遇到问题")
        print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
        return ""


def AskAI(content):
    dashscope.api_key = Dashscope_api_key
    messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': content}]
    response = Generation.call(model=Model_Choice, #qwen-72b-chat
                               messages = messages,
                               # 设置随机数种子seed，如果没有设置，则随机数种子默认为1234
                               seed = random.randint(1, 10000),
                               temperature=0.4,
                               top_p=0.8,
                               top_k=50,
                               # 将输出设置为"message"格式
                               result_format='message')
    if response.status_code == HTTPStatus.OK:
        response_str = response["output"]["choices"][0]["message"]["content"]
        response_str = re.sub(r'\n{2,}', '\n', response_str)
        print("大模型答复：")
        print(response_str)
        return response_str
    else:
        print("大模型反馈遇到问题")
        print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
        return ""



def AskAI_long(content):
    dashscope.api_key = Dashscope_api_key
    messages = [{'role': 'system', 'content': 'You are a financial summary expert with a focus on corporate annual reports.'},
                {'role': 'user', 'content': content}]
    response = Generation.call(model="qwen-long",
                               messages = messages,
                               # 设置随机数种子seed，如果没有设置，则随机数种子默认为1234
                               seed = random.randint(1, 10000),
                               temperature=0.8,
                               top_p=0.8,
                               top_k=50,
                               # 将输出设置为"message"格式
                               result_format='message')
    if response.status_code == HTTPStatus.OK:
        response_str = response["output"]["choices"][0]["message"]["content"]
        response_str = re.sub(r'\n{2,}', '\n', response_str)
        print("大模型答复：")
        print(response_str)
        return response_str
    else:
        print("大模型反馈遇到问题")
        print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
        return ""

# 由FrontEnd调用，判断是否正在询问企业信息
def judge_is_business(message, history):
    ask_content = \
f"""
请判断下面这段输入是否包含询问某企业相关情况的要求？回答是或者否（只要一个字）
内容：{message}
历史对话记录：{history}
"""
    for i in range(5): # 如果失败，最多重复十次
        try:
            response = AskAI(ask_content)
            if response == "是":
                return True
            elif response == "否":
                return False
            else:
                print("回答不符合格式，重新提问")
        except:
            print("获取判断“是否询问企业信息”失败")
            return False
    return False

def get_business_info_str(company, time):
    db, cursor = data_ctrl.Link2DataBusinessReportBase()
    df = data_ctrl.select_data(company, time, cursor)
    db.close()
    formatted_string = df.apply(lambda row: ' '.join(row.astype(str)), axis=1).str.cat(sep='\n')
    return formatted_string


# model_chat多轮对话套壳，加载天气相关信息后向大模型提问，返回生成器
def get_business_response(message, history, Overall_Brief_Info_List):

    company, time = ask_company_time(message, history, Overall_Brief_Info_List)

    business_info = get_business_info_str(company, time)

    reorganized_msg = \
f"""
请利用补充信息回答用户问题，不要在回答中提及补充信息的来源：
用户问题：{message};
补充企业信息：\n{business_info}；
答复要求：关注用户问题，精简回答内容。
"""

    from FrontEnd import model_chat
    response_gen = model_chat(reorganized_msg, history, 'You are a helpful assistance.')

    #print("大模型对话综合回复：", list(response_gen)[-1][1][-1][1])

    return response_gen

# 让大模型选定企业和时期信息
def ask_company_time(message, history, short_data_list):
    ask_content = \
f"""
请分析下面这段话询问了哪个企业、哪段时期的信息：
内容：{message};
历史对话记录：{history}
已知：今天的日期是{datetime.date.today()};
要求：按照以下格式回答,保留中括号；如果没有找到，将企业名称填写为“未找到”，时期填写为“未找到”。时期不区分上下半年。
[企业：企业名称]
[时期：xxxx年年度/xxxx年半年度/xxxx年x季度]
"""
    print(ask_content)
    for i in range(5):
        try:
            response = AskAI(ask_content)
            company = re.search("企业：(.*?)]", response).group(1)
            time = re.search("时期：(.*?)]", response).group(1)
            print("提取的企业和时期为：", company, time)
            if time[-3:]=="上半年" or time[-3:]=="下半年":
                time = time[:-3]+"半年度"
            if not re.match(r"^\d{4}年(年度|半年度|[一二三四]季度)$", time) and time!="未找到":
                raise ValueError
            return company, time
        except:
            print("回答不符合格式，重新提问")

    print("提取信息失败")
    return "", ""


if __name__=="__main__":
    db, cursor = data_ctrl.Link2DataBusinessReportBase()
    df = data_ctrl.select_data("西藏诺迪康药业股份有限公司", "2024年半年度", cursor)
    formatted_string = df.apply(lambda row: ' '.join(row.astype(str)), axis=1).str.cat(sep='\n')
    print(formatted_string)
    db.close()