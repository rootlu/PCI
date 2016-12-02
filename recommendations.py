# coding: utf-8
# author: luyf
# create_date: 2016.10.16


from math import sqrt

critics = {'Lisa Rose': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
                         'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 'The Night Listener': 3.0},
           'Gene Seymour': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 'Just My Luck': 1.5,
                            'Superman Returns': 5.0, 'You, Me and Dupree': 3.5, 'The Night Listener': 3.0},
           'Michael Phillips': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
                                'Superman Returns': 3.5, 'The Night Listener': 4.0},
           'Claudia Puig': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0, 'Superman Returns': 4.0,
                            'You, Me and Dupree': 2.5, 'The Night Listener': 4.5},
           'Mick LaSalle': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 'Just My Luck': 2.0,
                            'Superman Returns': 3.0, 'You, Me and Dupree': 2.0, 'The Night Listener': 3.0},
           'Jack Matthews': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 'Superman Returns': 5.0,
                             'You, Me and Dupree': 3.5, 'The Night Listener': 3.0},
           'Toby': {'Snakes on a Plane': 4.5, 'Superman Returns': 4.0, 'You, Me and Dupree': 1.0}}


def sim_distance(prefs, person1, person2):
    """
    Euclidean distance 欧几里德距离
    :param prefs:数据集
    :param person1:
    :param person2:
    :return:Similarity evaluation based on distance，用户1和用户2基于距离德相似度评价，介于0到1，1表示两人的评价完全一致
    """
    # get the list of shared_item
    si = {}
    for item in prefs[person1]:
        if item in prefs[person2]:
            si[item] = 1  # 两人同时评论过的商品

    # if two persons have no commons, return 0
    if len(si) == 0:
        return 0

    # 计算所有差值的平方
    sum_of_squares = sum([pow(prefs[person1][item] - prefs[person2][item], 2)
                          for item in prefs[person1] if item in prefs[person2]])
    return 1 / (1 + sqrt(sum_of_squares))  # 偏好越相近，相似度值越大


def sim_pearson(prefs, p1, p2):
    """
    Pearson correlation 皮尔逊相关度
    :param prefs:数据集
    :param p1:
    :param p2:
    :return: 介于-1到1之间的皮尔逊相关度值，1表示两人对每一件物品均有着完全一致的评价
    """
    si = {}
    for item in prefs[p1]:
        if item in prefs[p2]:
            si[item] = 1  # 两人同时评论过的商品

    # get the nums of si
    n = len(si)

    # if two persons has no commons, return 0
    if n == 0:
        return 0

    # 两人都评论过的商品，求其评分总和
    sum1 = sum([prefs[p1][it] for it in si])
    sum2 = sum([prefs[p2][it] for it in si])

    # 两人都评论过的商品，求其评分的平方和
    sum1_sq = sum([pow(prefs[p1][it], 2) for it in si])
    sum2_sq = sum([pow(prefs[p2][it], 2) for it in si])

    # 两人都评论过的商品，求评分乘积之和
    p_sum = sum([prefs[p1][it] * prefs[p2][it] for it in si])

    # 计算皮尔逊评价值
    num = p_sum - (sum1 * sum2 / n)
    den = sqrt((sum1_sq - pow(sum1, 2) / n) * (sum2_sq - pow(sum2, 2) / n))
    if den == 0:
        return 0
    r = num / den
    return r


def top_matches(prefs, person, n=5, similarity=sim_pearson):
    """
    计算一个人员列表，这些人与某个指定的人员具有相近的品味
    :param prefs:数据集
    :param person:指定人员
    :param n:最为相近的人数
    :param similarity:相似性参数，指向一个实际算法函数
    :return: top 5 matches persons 最为相近的n个人的列表
    """
    # 计算指定人员与其他人员的相似度值
    scores = [(similarity(prefs, person, other), other)
              for other in prefs if other != person]

    # sort the list of scores, the highest score is at the front
    scores.sort()
    scores.reverse()
    return scores[0:n]


def get_recommendations(prefs, person, similarity=sim_pearson):
    """
    基于用户的协作型过滤（user-based collaborative filtering）
    give recommendations for person 利用所有其他人的评价值的加权平均，为某人提供推荐
    :param prefs:
    :param person:
    :param similarity:
    :return:一个影片推荐列表
    """
    totals = {}
    sima_sums = {}
    for other in prefs:  # 不和自己比较
        if other == person:
            continue
        sim = similarity(prefs, person, other)  # 计算两个人的相似度
        if sim <= 0:  # ignore the values which is below zero or equal to zero
            continue
        for item in prefs[other]:
            # only deal with the movies that person doesn't watch
            if item not in prefs[person] or prefs[person][item] == 0:
                totals.setdefault(item, 0)
                totals[item] += prefs[other][item]*sim  # scores * similarities
                sima_sums.setdefault(item, 0)
                sima_sums[item] += sim  # sum of all persons' similarities

    rankings = [(total/sima_sums[item], item) for item, total in totals.items()]

    rankings.sort()
    rankings.reverse()
    return rankings


def transform_prefs(prefs):
    """
    transform persons to things
    :param prefs: 原始数据字典 {人名1：{电影1：评分，电影2：评分, ...}，人名2：{电影1：评分, ...}...}
    :return: 物品和人员对调后的数据字典
    """
    result = {}
    for person in prefs:
        for item in prefs[person]:  # item表示person 评论的所有电影
            result.setdefault(item, {})
            result[item][person] = prefs[person][item]  # 讲物品和人员对调
    return result


def calculate_similar_items(prefs, n=10):
    """
    构造一个包含相近物品的完整数据集
    :param prefs:数据集
    :param n: 最为相近的物品数量
    :return: 相近物品数据集
    """
    result = {}  # 建立字典，以给出与这些物品最为相近的所有其他物品
    item_prefs = transform_prefs(prefs)  # 以物品为中心，对偏好矩阵实施倒置处理
    count = 0
    for item in item_prefs:
        count += 1
        if count % 100 == 0:
            print "%d / %d" % (count, len(item_prefs))
        # 寻找最为相近的n个物品
        scores = top_matches(item_prefs, item, n=n, similarity=sim_distance)
        result[item] = scores
    return result


def get_recommended_items(prefs, item_match, user):
    """
    基于物品的过滤（item-based collaborative filtering）
    为某一用户user推荐商品
    :param prefs:数据集
    :param item_match:物品相似度
    :param user:用户
    :return:推荐商品列表
    """
    user_ratings = prefs[user]  # user评论过的商品字典
    scores = {}
    total_sim = {}

    # 循环遍历user评论过的商品
    for (goods_name, rating) in user_ratings.items():
        # 循环遍历与当前物品相近的物品
        for (similarity, item2) in item_match[goods_name]:
            # ignore goods that the user has commented on
            if item2 in user_ratings:
                continue
            scores.setdefault(item2, 0)
            scores[item2] += similarity*rating

            total_sim.setdefault(item2, 0)
            total_sim[item2] += similarity

    rankings = [(score/total_sim[goods_name], goods_name) for goods_name, score in scores.items()]

    rankings.sort()
    rankings.reverse()
    return rankings


def load_movies_lens(path='./data/ml-100k'):
    """
    加载电影数据
    :param path: 数据文件存储路径
    :return:数据集字典
    """
    # 获取影片标题
    movies = {}
    for line in open(path + '/u.item'):
        (movies_id, title) = line.split('|')[0:2]
        movies[movies_id] = title

    # 加载数据
    prefs = {}
    for line in open(path + '/u.data'):
        (user, movies_id, rating, ts) = line.split('\t')
        prefs.setdefault(user, {})
        prefs[user][movies[movies_id]] = float(rating)
    return prefs


# print 'Euclidean distance:'
# print sim_distance(critics, 'Lisa Rose', 'Gene Seymour')
#
# print 'Pearson correlation:'
# print sim_person(critics, 'Toby', 'Gene Seymour')
#
# print 'top 5 matches persons:'
# print top_matches(critics, 'Toby', n=3)

# print 'get recommendations:'
# print getRecommendations(critics, 'Toby')

# movies = transform_prefs(critics)
# print top_matches(movies, 'Superman Returns')

# print get_recommendations(movies, 'Just My Luck')

# 构造物品相似度的数据集
# item_sim = calculate_similar_items(critics)
# print item_sim
# print get_recommended_items(critics, item_sim, 'Toby')

# 加载数据，返回数据集字典
movie_prefs = load_movies_lens()
print movie_prefs['87']
print get_recommendations(movie_prefs, '87')[0:3]  # 获取基于用户的推荐

item_sim = calculate_similar_items(movie_prefs, n=50)  # 构造物品相似度字典
print get_recommended_items(movie_prefs, item_sim, '87')[0:3]  # 获取基于商品的推荐



