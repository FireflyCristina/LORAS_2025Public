import PyPDF2
import camelot
from pandas import DataFrame
import threading
import queue

import LLMControl as llm
import re

PDF_Direction = "D:\\Desktop\南京大学\\24人工智能+竞赛\企业年报PDF数据库"


def get_data_info(table_str, q, id):
    ask_content = table_str + \
                  """
结合以上表格信息，提取财务报表的主要信息。
如果没有找到某条数据，将数值填写为“No_Data”。
所有百分比数据整理为%的格式。
回答格式如下，要求保留所有方括号，仅在‘:’右侧的中括号中填写内容：
企业中文全称:[企业中文全称]
企业中文简称:[企业中文简称]
[营业收入]:[本期数值][上年同期][本报告期比上年同期增减]
[归属于上市公司股东的净利润]:[本期数值][上年同期][本报告期比上年同期增减]
[归属于上市公司股东的扣除非经常性损益的净利润]:[本期数值][上年同期][本报告期比上年同期增减]
[经营活动产生的现金流量净额]:[本期数值][上年同期][本报告期比上年同期增减]
[基本每股收益]:[本期数值][上年同期][本报告期比上年同期增减]
[稀释每股收益]:[本期数值][上年同期][本报告期比上年同期增减]
[加权平均净资产收益率]:[本期数值][上年同期][本报告期比上年同期增减]
[总资产]:[本期数值][上年同期][本报告期比上年同期增减]
[归属于上市公司股东的净资产]:[本期数值][上年同期][本报告期比上年同期增减]
[非经常性损益合计]:[数值]
"""
    print(ask_content)
    for i in range(5):
        try:
            response = llm.AskAI_turbo(ask_content)
            brief_name, matches = extract_data(response)  # 将数据整理成dataframe
            if brief_name == None or matches == None:
                raise ValueError
            print("基本数据信息提取完毕")
            q.put((brief_name, matches, id))
            return
        except:
            print("大模型回答不符合格式，数据提取失败")
    q.put((None, [None] * 38, id))
    return


def get_basic_info(PDF_file):
    with open(PDF_file.name, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        num_pages = len(reader.pages)
        print(f"Total number of pages: {num_pages}")

        title_time = list(get_title(PDF_file))
        if title_time[0]==None:
            title_time[0]=PDF_file.name
        if title_time[1]==None:
            title_time[1]="2024年上半年"
        contents = get_content_list(reader)
        yanfa = get_yanfa_cost(reader, PDF_file)

        # 运用大模型读取主要数据所在页和管理层讨论所在页
        ask_content = contents + \
"""
结合以上目录信息，回答“主要财务指标”和“管理层分析和讨论”两类信息所在的页码。
终止页数为下一节的起始页数减一。
回答格式如下（保留数字两侧的中括号）
[主要财务指标]:[起始页数]~[终止页数]
[管理层讨论与分析]:[起始页数]~[终止页数]
"""
        flag = False
        print(ask_content)
        while not flag:
            try:
                response = llm.AskAI_turbo(ask_content)
                datapages, discusspages = get_page_num(response)
                if datapages != None and discusspages != None:
                    flag = 1
            except:
                flag = 0
        print(datapages, discusspages)  # 两个值均为(start,end)的元组
        print()

        # 读datapage上的数据表格，并处理成可提供给大模型的字符串
        data_tables = read_PDF_tables(PDF_file, f"{datapages[0]}-{datapages[1]}")
        table_str = reorganize_tables(data_tables)
        # print(table_str)

        # 双线程并行询问大模型，提高速度
        result_q = queue.Queue()
        thread1 = threading.Thread(target=get_data_info, args=(table_str, result_q, "id_1"))
        thread2 = threading.Thread(target=get_future_dev_info, args=(PDF_file, discusspages, result_q, "id_2"))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        result1 = result_q.get()
        result2 = result_q.get()

        brief_name = result1[0] if result1[-1] == 'id_1' else result2[0]
        matches = result1[1] if result1[-1] == 'id_1' else result2[1]
        future_dev = result2[0] if result2[-1] == 'id_2' else result1[0]

        print()
        # 统合企业名称、报告时间、财务数据、研发支出、未来规划的所有数据
        match_table = [["企业名称", title_time[0], "企业简称", brief_name], ["报告时间", title_time[1], None, None],
                       matches[0:4], matches[4:8], matches[8:12], matches[12:16],
                       matches[16:20], matches[20:24], matches[24:28], matches[28:32],
                       matches[32:36], matches[36:38] + [None, None],
                       yanfa, ["主营业务和发展规划"] + future_dev]
        result_df = DataFrame(match_table, columns=["项目", "本报告期", "上年同期", "本报告期比上年同期增减"])

        print("信息整合完成：\n", result_df.to_string())
        return result_df


def read_PDF_text_all(PDF_name):
    with open(PDF_Direction + "\\" + PDF_name, 'rb') as file:
        reader = PyPDF2.PdfReader(file)

        # 获取 PDF 页面数
        num_pages = len(reader.pages)
        print(f"Total number of pages: {num_pages}")

        with open("text_file.txt", 'a', errors='ignore') as text_file:
            # 读取全部内容
            for page_index in range(num_pages):
                print(f"正在提取第{page_index}页的文本：")
                page = reader.pages[page_index]
                text = page.extract_text()
                print(text + '\n')
                text_file.write("<NEW PAGE>\n" + text + '\n')


def read_PDF_text(PDF_file, page=(1, 'end')):
    with open(PDF_file.name, 'rb') as file:
        reader = PyPDF2.PdfReader(file)

        # 获取 PDF 页面数
        num_pages = len(reader.pages)

        # 根据页码要求读取内容
        if page[1] == 'end':
            start, end = page[0] - 1, num_pages
        else:
            start, end = page[0] - 1, page[1]
        content = ''
        for page_index in range(start, end):
            print(f"正在提取第{page_index + 1}页的文本")
            page = reader.pages[page_index]
            text = page.extract_text()
            print(text + '\n\n')
            content = content + text + '\n'
        return content


def read_PDF_tables(PDF_file, page='1-end'):
    # 使用 Camelot 的 read_pdf 方法读取 PDF 文件中的表格
    tables = camelot.read_pdf(PDF_file.name, pages=page, flavor='lattice')

    # 获取表格数量
    print(f"Total tables extracted: {len(tables)}\n")

    # 查看表格的数据
    for i in range(len(tables)):
        df = tables[i].df
        # 替换未正常读取的字符
        df.replace(r'\(cid:5351\)', '康', inplace=True, regex=True)
        df.replace(r'\(cid:12184\)', '票', inplace=True, regex=True)
        df.replace(r'\(cid:11934\)', '确', inplace=True, regex=True)
        df.replace(r'\(cid:5424\)', '开', inplace=True, regex=True)
        df.replace(r'\(cid:5739\)', '总', inplace=True, regex=True)
        df.replace(r'\(cid:5719\)', '性', inplace=True, regex=True)
        df.replace(r'\n', '', inplace=True, regex=True)

        print(df)

    return tables  # tables是含有dataframe的列表


# 提取企业名称和报告时期
def get_title(PDF_file):
    content = read_PDF_text(PDF_file, (1, 1))
    ask_content = content + \
                  """
请在以上内容中找出企业的中文全名和本报告的时间信息。
回答格式如下(保留填写内容两侧的中括号)：
企业名称:[企业中文全名]
报告期:[本报告期]
其中报告期严格按照“20xx年年度/半年度/x季度”的格式书写，忽略具体报告发布日期，年份使用阿拉伯数字，年份和时期中间不要有空格。
"""

    for i in range(5):
        try:
            response = llm.AskAI(ask_content)
            matches = re.findall(r'\[(.*?)]', response)
            if not len(matches) == 2:
                raise IndexError
            time = matches[1]
            if time[-3:] == "上半年" or time[-3:] == "下半年":
                time = time[:-3] + "半年度"
            if not re.match(r"^\d{4}年(年度|半年度|[一二三四]季度)$", time):
                raise ValueError
            print(matches)
            return matches
        except:
            print("大模型答复不符合格式")
    return None, None


def get_yanfa_cost(reader, PDF_file):
    table_page = None
    search_key = "合并利润表"

    # 遍历 PDF 页数
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text = page.extract_text()

        # 检查 "合并利润表" 是否在这一页
        if search_key in text:
            table_page = page_num + 1  # Camelot 页码
            break
    if table_page is not None:
        for i in range(3):
            tables = camelot.read_pdf(PDF_file.name, pages=str(table_page + i))
            if len(tables)==0:
                tables = camelot.read_pdf(PDF_file.name, pages=str(table_page + i), flavor='stream')

            for i in range(len(tables)):
                df = tables[i].df
                # 替换未正常读取的字符
                df.replace(r'\(cid:5351\)', '康', inplace=True, regex=True)
                df.replace(r'\(cid:12184\)', '票', inplace=True, regex=True)
                df.replace(r'\(cid:11934\)', '确', inplace=True, regex=True)
                df.replace(r'\(cid:5424\)', '开', inplace=True, regex=True)
                df.replace(r'\(cid:5739\)', '总', inplace=True, regex=True)
                df.replace(r'\(cid:5719\)', '性', inplace=True, regex=True)
                df.replace(r'\n', '', inplace=True, regex=True)

            print("合并利润表：", tables)
            if len(tables)>0:
                print(reorganize_tables(tables))
            for j in range(len(tables)):
                df = tables[j].df
                for index, row in df.iterrows():
                    if "研发费用" in list(row.values):
                        print("研发费用：", row.values)
                        list1 = ["研发费用"]
                        counter = 0
                        for item in row.values[1:]:
                            if is_number(item) and counter < 2:
                                list1.append(item)
                                counter += 1
                        if counter == 2:
                            list1.append(get_ratio(list1[1], list1[2]))
                        print(list1)
                        return list1

        return ["研发费用", 'None', 'None', 'None']


def is_number(value):
    try:
        print(value)
        value = value.replace(',', '')
        value = value.replace('，', '')
        value = value.strip()
        float(value)  # 去除逗号，尝试转换为浮点数
        return True
    except ValueError:
        return False


def get_ratio(a, b):
    try:
        a_value = float(a.replace(',', ''))  # 去除逗号，尝试转换为浮点数
        b_value = float(b.replace(',', ''))
        return f"{(a_value / b_value - 1) * 100:.2f}%"
    except ValueError:
        return False


def extract_data(response):
    try:
        matches = re.findall(r'\[(.*?)]', response)
        if len(matches) == 40:
            return matches[1], matches[2:]
        else:
            print("大模型回答不符合格式")
            return None, None
    except:
        print("大模型回答不符合格式")
        return None, None


# 将dataframe构成的列表转化为标准化字符串。列表字符串空格为一列，换行为一行。
def reorganize_tables(tables):
    content = ''
    for i in range(len(tables)):
        table = tables[i].df
        for index, row in table.iterrows():
            for colname, value in row.items():
                content = content + str(value) + ' '
            content += '\n'
        content += '\n'
    return content


# 从大模型回答字符串中获取财务指标所在页码和管理层分析所在页码
def get_page_num(response):
    try:
        data_start = re.search("指标]:\\[(.*?)]", response).group(1)
        data_end = re.search("指标]:\\[(.*?)]~\\[(.*?)]", response).group(2)
        discuss_start = re.search("分析]:\\[(.*?)]", response).group(1)
        discuss_end = re.search("分析]:\\[(.*?)]~\\[(.*?)]", response).group(2)

        data = (int(data_start.strip()), int(data_end.strip())+1)
        discuss = (int(discuss_start.strip()), int(discuss_end.strip())+1)

        if data[1] - data[0] > 0 and discuss[1] - discuss[0] > 0:
            print("提取的主要财务指标页码和管理层分析页码为：", data, discuss)
            return data, discuss
        else:
            raise ValueError
    except:
        print("大模型回答不符合格式")
        return None, None


# 从PDF文档中获取目录页的信息
def get_content_list(reader):
    num_pages = len(reader.pages)
    for i in range(num_pages):
        text = reader.pages[i].extract_text()
        matches = re.findall(r'\s+目录\s+', text)
        if matches:
            return text
    return False


def get_future_dev_info(PDF_file, pages, q, id):
    text_all = ""
    if pages[1] > pages[0] + 7:
        pages = (pages[0], pages[0] + 7)
    for page in range(pages[0], pages[1] + 1):

        text = read_PDF_text(PDF_file, (page, page))
        text_all += text

        if re.search(r'\s+主要财务数据同比变动情况\s+', text) != None \
                or re.search(r'\s+四、', text) != None:
            break
    ask_content = text_all + \
                  """\n
根据以上文本，从“主营业务与行业地位”、“核心竞争力”、“发展规划”三个方面进行每个方面300字左右的摘要总结。输出格式如下（保留中括号）：
[主营业务与行业地位]:[摘要文本]
[核心竞争力]:[摘要文本]
[发展规划]:[摘要文本]
"""
    response = llm.AskAI_long(ask_content)

    try:
        ans1 = re.search(r'\[主营业务与行业地位][:：](.*?)\n', response).group(1)
        ans2 = re.search(r'\[核心竞争力][:：](.*?)\n', response).group(1)
        ans3 = re.search(r'\[发展规划][:：](.*)', response).group(1)
        print("文本信息提取如下", ans1, ans2, ans3, sep='\n')
        q.put(([ans1, ans2, ans3], id))
        return
    except:
        print("文本信息提取出现问题")
        q.put(([None, None, None], id))
        return


class TempPDF_Name:
    def __init__(self, name):
        self.name = PDF_Direction + '\\' + name


PDF_namelist = ["北京科锐：2024年半年度报告.PDF", "鹏鼎控股：2024年半年度报告.PDF",
                "西藏药业：西藏药业2023年半年度报告全文.PDF", "德赛电池：2024年半年度报告.PDF"]

if __name__ == "__main__":
    for i in [3]:
        df = get_basic_info(TempPDF_Name(PDF_namelist[i]))  # 在这里可以控制读取哪一篇PDF
        #df.to_csv(f"{PDF_namelist[i][:-4]}.csv", index=True, encoding='utf-8-sig')
