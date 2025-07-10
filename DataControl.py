from pandas import DataFrame, read_csv
import pymysql as sql

# 设定所有column的列名和参数字符串长度
column_list = \
    [
        "企业名称", "企业简称", "报告时间",
        "本期营业收入", "上期营业收入", "营业收入增长率",
        "本期归属股东净利润", "上期归属股东净利润", "股东净利润增长率",
        "本期归属股东的扣除非经常性损益的净利润", "上期归属股东的扣除非经常性损益的净利润",
        "归属股东的扣除非经常性损益的净利润增长率",
        "本期现金流量净额", "上期现金流量净额", "现金流量净额增长率",
        "本期基本每股收益", "上期基本每股收益", "基本每股收益增长率",
        "本期稀释每股收益", "上期稀释每股收益", "稀释每股收益增长率",
        "本期加权平均净资产收益率", "上期加权平均净资产收益率", "加权平均净资产收益率增长率",
        "本期总资产", "上期总资产", "总资产增长率",
        "本期归属股东净资产", "上期归属股东净资产", "归属股东净资产增长率",
        "非经常性损益合计",
        "本期研发费用", "上期研发费用", "研发费用增长率",
        "主营业务与行业地位", "核心竞争力", "发展规划"
    ]

string_size_list = (100,) + (50,) * 2 + (60,) * 31 + (800,) * 3


# 连接到数据库BusinessReportDatabase
def Link2DataBusinessReportBase():
    db = sql.connect(host='localhost', user='YOUR_MYSQL_USERNAME', password='YOUR_MYSQL_PASSWORD', database='BusinessReportDatabase')
    cursor = db.cursor()
    return db, cursor


# 清空数据库（删除BusinessReportData数据表），仅限本项目适用
def clear_database(db, cursor):
    delete_cmd = \
        """
DROP TABLE IF EXISTS BusinessReportData;
"""
    print(f"正在清空BusinessReportDatabase数据库：\n", delete_cmd)
    try:
        cursor.execute(delete_cmd)
        db.commit()
        return True
    except:
        db.rollback()
        print(f"MySQL指令执行失败，清空数据库失败")
        return False


# 根据参数创建数据表
def create_table(cursor, table_name, column_list, string_size_list=tuple()):
    # 检查表名和列名是否全部合法
    for name in [table_name] + column_list:
        if not (type(name) == str and name.isidentifier()):
            print("表名或列名不合法，创建表格失败")
            return False

    # 默认字段字符串长度为100
    if len(string_size_list) == 0:
        string_size_list = (100,) * len(column_list)

    if len(column_list) != len(string_size_list):
        print("列数和所给字符串长度列表不匹配，创建表格失败")
        return False

    # 创建数据表
    CreateTableCmd = \
        f"""
CREATE TABLE  IF NOT EXISTS {table_name} (
id INT AUTO_INCREMENT PRIMARY KEY,
"""
    for i in range(len(column_list) - 1):
        CreateTableCmd += f"{column_list[i]} VARCHAR({string_size_list[i]}),\n"
    CreateTableCmd += f"{column_list[-1]} VARCHAR({string_size_list[-1]})\n)CHARACTER SET utf8mb4;\n"

    try:
        cursor.execute(CreateTableCmd)
        return True
    except:
        print(f"MySQL指令执行失败，创建数据表{table_name}失败")
        return False


# 将dataframe的数据展开后存入数据表, 返回企业名称和报告时期的二元元组
def store_data(df, db, cursor):
    # 尝试新建数据表，如果已存在则不会新建
    create_table(cursor, "BusinessReportData", column_list, string_size_list)

    # 展平df中的数据为列表
    data_list = df.values.ravel().tolist()
    data_list = data_list[1:2] + data_list[3:4] + data_list[5:6] + data_list[9:12] + data_list[13:16] + \
                data_list[17:20] + data_list[21:24] + data_list[25:28] + data_list[29:32] + \
                data_list[33:36] + data_list[37:40] + data_list[41:44] + data_list[45:46] + \
                data_list[49:52] + data_list[53:56]

    # print(data_list)

    insert_data_cmd = \
        f"""
INSERT INTO BusinessReportData
VALUES(
NULL,
"""
    for i in range(len(data_list) - 1):
        insert_data_cmd += f'"{data_list[i]}",\n'
    insert_data_cmd += f'"{data_list[-1]}");'

    # print(insert_data_cmd)

    try:
        cursor.execute(insert_data_cmd)
        db.commit()
        print("数据已存入BusinessReportData数据表")
    except:
        db.rollback()
        print("向数据表BusinessReportData插入数据失败")
    return data_list[1],data_list[2]  # 返回公司名称，便于维护搜索列表


# 根据给定的公司名称，将数据库中的数据整理成dataframe返回
def select_data(company_name, report_time, cursor):
    if report_time=="未找到":
        select_cmd = \
f"""
SELECT * FROM BusinessReportData WHERE ( 企业名称 = '{company_name}' OR 企业简称 = '{company_name}' );
"""
    else:
        select_cmd = \
f"""
SELECT * FROM BusinessReportData WHERE ( 企业名称 = '{company_name}' OR 企业简称 = '{company_name}' ) AND 报告时间 = '{report_time}';
"""
    print(select_cmd)
    try:
        cursor.execute(select_cmd)
        result = cursor.fetchall()
        print("数据库查询结果：",result)
        data_list = list(result[0])
        if len(data_list) != 38:
            raise IndexError
    except:
        print("未能从数据表获取该企业的相关数据")
        return DataFrame(["未能从数据表获取该企业的相关数据"])

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
    return result_df


if __name__ == "__main__":
    db, cursor = Link2DataBusinessReportBase()

    clear_database(db, cursor)

    # import ReadReport as rr
    # df = rr.get_basic_info(rr.PDF_namelist[0])

    df = read_csv("dataframe_example.csv", index_col=0, encoding='utf-8-sig')  # 调试用示例数据
    store_data(df, db, cursor)

    select_data("鹏鼎控股（深圳）股份有限公司", "2024年半年度", cursor)

    db.close()
