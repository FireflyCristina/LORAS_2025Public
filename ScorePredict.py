import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from PIL import Image

plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定用于显示的font
plt.rcParams['axes.unicode_minus'] = False   # 解决负号'-'显示为方块的问题

def get_scores(df):
    dict1= {"综合评分":8.0,
            "创新能力":8.5,
            "发展速度":7.4,
            "竞争力":7.6,
            "盈利能力":8.3,
            "风险控制":7.2}
    return dict1

def create_radar_chart(scores):
    dict1 = scores
    # 数据设置
    labels = np.array(['创新能力', '发展速度', '风险控制', '竞争力', '盈利能力'])
    value_list = list(dict1.values())
    num_vars = len(labels)

    # 计算角度
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles = [angle + np.pi / 2 for angle in angles]  # 旋转90度，使第一个顶点朝上
    angles = [angle-2*np.pi if angle>2*np.pi else angle for angle in angles ]
    values=value_list[1:]

    print(angles, values)

    # 完成循环
    values = np.concatenate((values,[values[0]]))
    angles += angles[:1]

    # 绘图
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color='red', alpha=0.25)
    ax.plot(angles, values, color='red', linewidth=2)

    # 标签设置
    ax.set_ylim(0, 10)  # Y轴区间为0到10
    ax.set_yticks([2,4,6,8,10])  # 设置刻度显示
    ax.set_yticklabels(['2', '4', '6', '8', '10'])  # 显示的刻度标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    # 使用 BytesIO 保存图像为内存流
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)  # 关闭图像以释放内存

    image = Image.open(buf)

    return image


if __name__=="__main__":
    pass