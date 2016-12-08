# coding: utf-8
# author: luyf
# create-date: 2016.10.19
import time
from pydelicious import get_popular, get_userposts, get_urlposts


def initialze_user_dict(tag, count=5):
    user_dict = {}
    # 获取前count个最受欢迎的链接张贴记录
    for p1 in get_popular(tag=tag)[0:count]:
        for p2 in get_urlposts(p1['url']):  # 此处与书中不同，现在返回字典的'href' 键已经改为 'url'
            user = p2['user']
            user_dict[user] = {}
    return user_dict


def fill_items(user_dict):
    all_items = {}
    # 查找所有用户都提交过的链接
    for user in user_dict:
        for i in range(3):
            try:
                posts = get_urlposts(user)
                break
            except:
                print 'Failed user' + user + ', retrying'
                time.sleep(4)
        for post in posts:
            url = post['url']
            user_dict[user][url] = 1
            all_items[url] = 1
    # 用0填充缺失的内容
    for ratings in user_dict.values():
        for item in all_items:
            if item not in ratings:
                ratings[item] = 0


# print get_popular(tag='programming')
delusers = initialze_user_dict('programming')
delusers['tsegaran'] = {}
fill_items(delusers)
print delusers
