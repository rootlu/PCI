# coding: utf-8
# author: luyf
# create date: 2016.11.28

import feedparser
import re


def get_word_counts(url):
    """
    返回一个RSS订阅源的标题和包含单词计数情况的字典
    :param url:
    :return:一个博客标题和单词个数字典
    """
    # 解析订阅源
    url_parser = feedparser.parse(url)
    word_count = {}

    # 循环遍历所有的文章条目
    for each_entry in url_parser.entries:
        if 'summary' in each_entry:
            summary = each_entry.summary
        else:
            summary = each_entry.description

        # 提取一个单词列表
        words = get_words(each_entry.title+' '+summary)
        for each_word in words:
            word_count.setdefault(each_word, 0)
            word_count[each_word] += 1
    return url_parser.feed.title, word_count


def get_words(html):
    """
    去除参数htl中的所有标签，以非字母字符作为分隔符拆分出单词
    :param html:
    :return: 一个单词列表
    """
    # 去除所有HTML标签
    txt = re.compile(r'<[^>]+>').sub('', html)
    # 利用所有非字母字符拆分出单词
    words = re.compile(r'[^A-Z^a-z]+').split(txt)
    # 转化成小写形式
    return [each_word.lower() for each_word in words if each_word != '']

apcount = {}  # 出现某些单词的博客数目
title_word_counts_dict ={}  # 博客标题和单词统计字典的 字典
feed_list = [line for line in file('./data/test.txt')]
for feed_url in feed_list:
    title, word_count_dict = get_word_counts(feed_url)
    title_word_counts_dict[title] = word_count_dict
    for word, count in word_count_dict.items():
        apcount.setdefault(word, 0)
        if count > 0:  #
            apcount[word] += 1

word_list = []  # 单词列表，统计 在博客中出现次数满足一定百分比 的单词
for word, blog_count in apcount.items():
    frac = float(blog_count)/len(feed_list)
    if 0.1 < frac < 0.5:
        word_list.append(word)

out = file('blog_data.txt', 'w')
out.write('Blog')
for word in word_list:
    out.write('\t%s' %word)
out.write('\n')
for blog_title, each_word_count_dict in title_word_counts_dict.items():
    out.write(blog_title)
    for word in word_list:  # 对于 在博客中出现次数满足一定百分比的 单词
        if word in each_word_count_dict:  # 该单词在该博客中也出现了
            out.write('\t%d' % each_word_count_dict[word])  # 记录该单词在该博客中出现的次数
        else:
            out.write('\t0')
    out.write('\n')
