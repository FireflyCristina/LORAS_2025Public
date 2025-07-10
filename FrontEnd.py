import gradio as gr
from http import HTTPStatus
from pandas import DataFrame, concat
import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role
from typing import List, Optional, Tuple, Dict
from urllib.error import HTTPError
import threading


import LLMControl as llm
import DataControl as data_ctrl
import ReadReport as rr
import judge

default_system = 'You are a helpful assistant.'

# TODO：设置大模型API

dashscope.api_key = 'YOUR_DASHSCOPE_API_KEY'

History = List[Tuple[str, str]]
Messages = List[Dict[str, str]]

Overall_Brief_Info_List = []
Overall_Brief_Info_Dataframe = DataFrame(columns=["企业名称","报告时期"])


def history_to_messages(history: History, system: str) -> Messages:
    messages = [{'role': Role.SYSTEM, 'content': system}]
    for h in history:
        messages.append({'role': Role.USER, 'content': h[0]})
        messages.append({'role': Role.ASSISTANT, 'content': h[1]})
    return messages


def messages_to_history(messages: Messages) -> Tuple[str, History]:
    assert messages[0]['role'] == Role.SYSTEM
    system = messages[0]['content']
    history = []
    for q, r in zip(messages[1::2], messages[2::2]):
        history.append([q['content'], r['content']])
    return system, history


def model_chat(query: Optional[str], history: Optional[History], system: str
) -> Tuple[str, History, str]:
    if query is None:
        query = ''
    if history is None:
        history = []
    messages = history_to_messages(history, system)
    messages.append({'role': Role.USER, 'content': query})
    # TODO：切换模型配置
    gen = Generation.call(
        model = "qwen-max",
        messages = messages,
        result_format='message',
        stream=True
    )
    for response in gen:
        if response.status_code == HTTPStatus.OK:
            role = response.output.choices[0].message.role
            response = response.output.choices[0].message.content
            system, history = messages_to_history(messages + [{'role': role, 'content': response}])
            yield '', history, system
        else:
            raise HTTPError('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))


# model_chat生成器套壳，重新规划输入输出格式，并根据生成器内容实时更新chatbot对话框显示内容
def chatbot_response(message, chatbot_history):
    print("message:",message)
    print(chatbot_history)

    if llm.judge_is_business(message, chatbot_history):
        response_gen = llm.get_business_response(message, chatbot_history, Overall_Brief_Info_List)
    else:
        response_gen = model_chat(message, chatbot_history, default_system)
    index=0
    for res in response_gen:
        response = res[1][-1][1]
        if index!=0:
            chatbot_history.pop()
        chatbot_history.append((message, response))
        index+=1
        yield "", chatbot_history


# 清除对话内容的回调函数
def clear_chatbot():
    return "",[] # 返回空的对话历史




def switch_data_table(index):
    print(type(index),index)
    try:
        index=int(index)
        if index>len(Overall_Brief_Info_Dataframe) or index<1:
            raise ValueError
    except:
        print("输入值错误")
        return gr.update(), gr.update(), gr.update()


    db, cursor = data_ctrl.Link2DataBusinessReportBase()
    select_cmd = \
f"""
SELECT * FROM BusinessReportData WHERE id = {index};
"""
    try:
        cursor.execute(select_cmd)
        result = cursor.fetchall()
        print("数据库查询结果：", result)
        data_list = list(result[0])
        if len(data_list) != 38:
            raise IndexError
    except:
        print("未能从数据表获取相关数据")
        empty_df = DataFrame([["未能从数据表获取相关数据",None,None,None]],columns=["项目", "本报告期", "上年同期", "本报告期比上年同期增减"])
        return empty_df, gr.update(), gr.update()

    # 重整数据结构
    data_list = data_list[1:]
    match_table = [["企业名称", data_list[0], "企业简称", data_list[1]], ["报告时间", data_list[2], None, None],
                ["营业收入"] + data_list[3:6], ["归属于上市公司股东的净利润"] + data_list[6:9],
                ["归属于上市公司股东的扣除非经常性损益的净利润"] + data_list[9:12],
                ["经营活动产生的现金流量净额"] + data_list[12:15], ["基本每股收益"] + data_list[15:18],
                ["稀释每股收益"] + data_list[18:21],
                ["加权平均净资产收益率"] + data_list[21:24], ["总资产"] + data_list[24:27],
                ["归属于上市公司股东的净资产"] + data_list[27:30],
                ["非经常性损益合计", data_list[30], None, None], ["研发费用"] + data_list[31:34],
                ["主营业务和发展规划"] + data_list[34:37]]
    result_df = DataFrame(match_table, columns=["项目", "本报告期", "上年同期", "本报告期比上年同期增减"])
    print("提取数据完毕：\n", result_df)
    db.close()

    import ScorePredict as score
    scores = judge.get_scores(result_df)
    radar_img = score.create_radar_chart(scores)
    mkd_str = (f"<h2>综合评分 {scores['综合评分']}</h2><br>")
    for key, score in scores.items():
        if key != "综合评分":
            mkd_str += f"<h4>  {key}： {score:.1f}</h4><br>"

    return result_df, gr.update(value=radar_img, height=520), gr.update(value=mkd_str)


def receive_file(file):
    df = rr.get_basic_info(file)  # 提取信息

    db, cursor = data_ctrl.Link2DataBusinessReportBase()
    company, time = data_ctrl.store_data(df, db, cursor)  # 存入数据库
    db.close()

    company_time_pair_str = f"[{company} {time}]"
    global Overall_Brief_Info_List
    Overall_Brief_Info_List.append(company_time_pair_str)  # 留下简单记录

    newdata = DataFrame([{"企业名称": company, "报告时期": time}])
    global Overall_Brief_Info_Dataframe
    Overall_Brief_Info_Dataframe = concat([Overall_Brief_Info_Dataframe, newdata],
                                                 ignore_index=True)

    import ScorePredict as score
    scores = judge.get_scores(df)
    radar_img = score.create_radar_chart(scores)
    mkd_str = (f"<h2>综合评分 {scores['综合评分']}</h2><br>")
    for key, score in scores.items():
        if key!="综合评分":
            mkd_str += f"<h4>  {key}： {score:.1f}</h4><br>"

    return df, Overall_Brief_Info_Dataframe, gr.update(value=radar_img, height=520), gr.update(value=mkd_str)


def switch_data_score(view):
    if view=="Dataframe":
        return gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=True)


# 主程序从这里开始

if __name__ == "__main__":
    #清空数据库
    db, cursor = data_ctrl.Link2DataBusinessReportBase()
    data_ctrl.clear_database(db, cursor)
    db.close()

    with gr.Blocks() as demo:

        with gr.Row(): # 整体界面横向分为左右两个部分
            with gr.Column(): # 标题、文件入口、数据框纵向排列
                with gr.Row():
                    # logo和标题
                    gr.Image(value="LORASlogo.jpg", height=150, show_share_button=False, show_download_button=False, container=False)

                # PDF文档入口
                pdf_input = gr.File(label = "UPLOAD YOUR PDF FILE HERE", file_types=[".pdf"], file_count="single")
                gr.HTML('''<div style="color: #B0B0B0;">每份文档的信息提取和概要生成需要约30s的时间，请您耐心等待。</div>''')

                # 概括表格和行数选择区
                with gr.Row():
                    # 仅包含企业简称和报告期的数据列表
                    file_table_output = gr.DataFrame(label="已处理的数据列表", value=Overall_Brief_Info_Dataframe, interactive=False, height=130)
                    with gr.Column():
                        select_row_input = gr.Textbox(label="请输入要查询的数据编号", value='1', lines=1)  # 选择数据行数输入框
                        update_table_button = gr.Button("Select")  # 选择数据行数的按钮

                # 数据展示主表
                column_name_df = DataFrame(columns=["项目","本报告期","上年同期","本报告期比上年同期增减"])
                data_table_output = gr.DataFrame(label="从文件中提取的数据", interactive=False, wrap=True, height=500,
                                                 value=column_name_df, visible=True)

                with gr.Row(visible=False) as score_output:  # 初始不可见的评分信息显示组件
                    score_img_output = gr.Image(value="LORASlogo.jpg", height=150, label="评分五维能力图")
                    score_text_output = gr.Markdown("")

                with gr.Row():
                    btn_dataframe = gr.Button("数据表格")
                    btn_plot = gr.Button("评分信息")

                # 选择数据行数的按钮动作
                update_table_button.click(fn=switch_data_table, inputs=select_row_input, outputs=[data_table_output,
                                                                                score_img_output, score_text_output])
                # 传入文件，与两个表格显示联动的动作
                pdf_input.upload(fn=receive_file, inputs=pdf_input, outputs=[data_table_output, file_table_output,
                                                                         score_img_output, score_text_output])

                # 设置切换数据表格和评分信息的按钮动作
                btn_dataframe.click(
                    switch_data_score,
                    inputs=gr.Text(value="Dataframe",visible=False),
                    outputs=[data_table_output, score_output]
                )

                btn_plot.click(
                    switch_data_score,
                    inputs=gr.Text(value="Plot",visible=False),
                    outputs=[data_table_output, score_output]
                )


            # 智能问答对话框和输入框
            with gr.Column(): # 对话框和输入框纵向排列
                out_chatbot = gr.Chatbot(label='通义千问 企业数据扩展', elem_id="chatbox", height=780)
                ipt_textbox = gr.Textbox(label="Messages", placeholder="Type your message HERE", lines=5,
                                         interactive=True, autoscroll=True, autofocus=True)
                with gr.Row(): # 对话按钮横向排列
                    clear_button = gr.Button("Clear")
                    clear_button.click(fn=clear_chatbot, inputs=None, outputs=[ipt_textbox, out_chatbot])
                    submit_button = gr.Button("Submit")
                    submit_button.click(fn=chatbot_response, inputs=[ipt_textbox, out_chatbot],
                                        outputs=[ipt_textbox, out_chatbot])

    demo.queue(api_open=False)
    demo.launch(inbrowser=True, share=True)

