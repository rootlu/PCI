# coding: utf-8
# author: luyf
# create date: 2016.12.01

from math import sqrt
from PIL import Image, ImageDraw


class Bicluster:
    def __init__(self, vec, left=None, right=None, distance=0.0, id=None):
        self.left = left
        self.right = right
        self.vec = vec
        self.id = id
        self.distance = distance


def pearson(v1, v2):
    """
    求v1和v2的皮尔逊相似度，介于-1 和1 之间
    :param v1:数字列表
    :param v2:
    :return:
    """
    # 简单求和
    sum1 = sum(v1)
    sum2 = sum(v2)

    # 求平方和
    sum1_pow = sum([pow(v, 2) for v in v1])
    sum2_pow = sum([pow(v, 2) for v in v2])

    # 求乘积之和
    pearson_sum = sum([v1[i]*v2[i] for i in range(len(v1))])

    # 计算r （Peasrson score）
    num = pearson_sum - (sum1 * sum2 / len(v1))  # 乘积之和 - 和的乘积/数量
    den = sqrt((sum1_pow-pow(sum1, 2)/len(v1)) * (sum2_pow-pow(sum2, 2)/len(v2)))
    if den == 0:
        return 0
    return 1.0 - num/den  # 1-Pearson score,值越大，元素距离越小，介于0 到 1 之间，1表示两者完全匹配


def read_file(file_name):
    """
    记载数据文件
    Blog    word1   word2   ...
    blog1   b1_wc1  b1_wc2  ...
    blog2   b2_wc1  b2_wc2  ...
    ...
    :param file_name:文件名
    :return: 标题列表、行名列表、数据列表
    """
    lines = [line for line in file(file_name)]
    # 第一行是列标题
    col_names = lines[0].strip().split('\t')[1:]  # 以'\t'分割lines[0]，第一个元素为'Blog',从第二个元素开始为单词
    row_names = []
    data = []  # 每一项对应数据集中的一行数据
    for line in lines[1:]:  # 从第二行开始循环
        p = line.strip().split('\t')
        # 每一行的第一列是行名
        row_names.append(p[0])
        # 剩余部分是改行对应的数据
        data.append([float(x) for x in p[1:]])
    return row_names, col_names, data


def hcluster(rows, similarity=pearson):
    """
    分级聚类
    :param rows:数据集
    :param similarity: 距离计算方法，皮尔逊相关度
    :return:聚类后的根节点
    """
    distances = {}
    current_clust_id = -1

    # 最开始的聚类就是数据集中的每一行
    clust = [Bicluster(rows[i], id=i) for i in range(len(rows))]
    while len(clust)>1:
        lowest_pair = (0, 1)  # 初始的两个群组
        closest = similarity(clust[0].vec, clust[1].vec)  # 计算初始两个群组间的相似度 作为 初始的 最小距离
        # 遍历每一个配对，寻找最小距离
        for i in range(len(clust)):
            for j in range(i+1, len(clust)):  # 从第i+1开始，计算第i个群组和第i+1到最后一个群组之间的距离
                # 用distances来缓存距离的计算值
                if(clust[i].id, clust[j].id) not in distances:  # 还未计算i，j之间的距离
                    distances[(clust[i].id, clust[j].id)] = similarity(clust[i].vec, clust[j].vec)
                tmp_distance = distances[(clust[i].id, clust[j].id)]

                if tmp_distance < closest:  # 两个群组间的距离小于当前最小距离，重写最小距离
                    closest = tmp_distance
                    lowest_pair = (i, j)  # 记录当前距离最近的两个群组

        # 计算两个聚类的平均值
        merge_vec = [
            (clust[lowest_pair[0]].vec[i]+clust[lowest_pair[1]].vec[i])/2.0
            for i in range(len(clust[0].vec))
        ]
        # 建立新的聚类
        new_cluster = Bicluster(merge_vec, left=clust[lowest_pair[0]],
                                right=clust[lowest_pair[1]],
                                distance=closest, id=current_clust_id)

        # 不在原始集合中的聚类，其ID为负数
        current_clust_id -= 1
        del clust[lowest_pair[1]]
        del clust[lowest_pair[0]]
        clust.append(new_cluster)
    return clust[0]


def print_clust(clust, labels=None, n=0):
    """
    递归遍历聚类树，将其以类似文件系统层级结构的形式打印出来
    :param clust:
    :param labels:
    :param n:
    :return:
    """
    # 利用缩进来建立层级布局
    for i in range(n):
        print ' '
    if clust.id < 0:
        # 负数标记代表这是一个分支
        print '-'
    else:
        # 证书标记代表这是一个叶子节点
        if labels is None:
            print clust.id
        else:
            print labels[clust.id]

    # 现在开始打印左侧分支和右侧分支
    if clust.left is not None:
        print_clust(clust.left, labels=labels, n=n+1)
    if clust.right is not None:
        print_clust(clust.right, labels=labels, n=n+1)


def get_height(clust):
    """
    获取聚类的总体高度
    :param clust: 聚类
    :return: 聚类的高度
    """
    # 叶节点，高度为1
    if clust.left is None and clust.right is None:
        return 1
    return get_height(clust.left)+get_height(clust.right)


def get_depth(clust):
    """
    获取根节点的总体误差，节点误差深度等于每个分支的最大可能误差
    :param clust:
    :return:
    """
    # 一个叶节点的距离是0.0
    if clust.left is None and clust.right is None:
        return 0
    # 一个枝节点的距离等于左右两侧分支中距离较大者，加上该节点的自身距离
    return max(get_depth(clust.left), get_depth(clust.right)) + clust.distance


def draw_dendrogram(clust, labels, jpeg='clusters.jpg'):
    """
    为聚类创建一个高度为20像素，宽度国定的图片
    :param clust:
    :param labels:
    :param jpeg:
    :return:
    """
    # 高度和宽度
    height = get_height(clust)*20
    width = 1200
    depth = get_depth(clust)

    # 由于宽度是固定的，所以需要对距离值做相应的调整
    scaling = float(width-150)/depth

    # 新建一个白色背景的图片
    img = Image.new('RGB', (width, height),(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.line((0, height/2, 10, height/2), fill=(255, 0, 0))

    # 画第一个节点
    draw_node(draw, clust, 10, (height / 2), scaling, labels)
    img.save(jpeg, 'JPEG')


def draw_node(draw, clust, x, y, scaling, labels):
    """
    函数接受一个聚类及其位置信息，函数取到子节点的高度，并计算这些节点所在的位置
    用线条将他们连接起来，包括一条垂直线，两条水平线，水平线的长度由聚类中的误差值决定
    水平线越长，合并在一起的两个聚类差别越大
    :param draw:
    :param clust: 聚类
    :param x:
    :param y:
    :param scaling:
    :param labels:
    :return:
    """
    if clust.id < 0:
        h1 = get_height(clust.left)*20
        h2 = get_height(clust.right)*20
        top = y - (h1+h2)/2
        bottom = y + (h1+h2)/2
        # 线的长度
        line_len = clust.distance*scaling
        # 聚类到其子节点的垂直线
        draw.line((x, top+h1/2, x, bottom-h2/2), fill=(255, 0, 0))
        # 链接左侧节点的水平线
        draw.line((x, bottom-h2/2, x+line_len, bottom-h2/2), fill=(255, 0, 0))
        # 调用函数绘制左右节点
        draw_node(draw, clust.left, x + line_len, top + h1 / 2, scaling, labels)
        draw_node(draw, clust.right, x + line_len, bottom - h2 / 2, scaling, labels)
    else:
        # 叶节点，绘制节点标签
        draw.text((x+5, y-7), labels[clust.id], (0, 0, 0))


def rotate_matrix(data):
    """
    转置数据
    :param data:
    :return:
    """
    new_data = []
    for i in range(len(data[0])):
        new_row = [data[j][i] for j in range(len(data))]
        new_data.append(new_row)
    return new_data

blog_names_list, words_list, data_list = read_file('blog_data.txt')

# 分级聚类
# clust = hcluster(data_list)
# print_clust(clust, labels=blog_names_list)
# draw_dendrogram(clust, blog_names_list, jpeg='blogclust.jpg')

# 列聚类
rotate_data_list = rotate_matrix(data_list)
word_clust = hcluster(rotate_data_list)
draw_dendrogram(word_clust, labels=words_list, jpeg='wordclust.jpg')