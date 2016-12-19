# coding: utf-8
# author: luyf
# create date: 2016.12.05

import urllib2

import re
from bs4 import BeautifulSoup
from urlparse import urljoin
from pysqlite2 import dbapi2 as sqlite
import chardet
import jieba


# 构造一个单词列表，这些单词被忽略
IGNORE_WORDS = set(['the', 'of', 'to', 'and', 'a', 'in', 'is', 'it',
                    u'是', u'的', u'它', u'他', u'她', u'也'])
CRAWLER_DEPTH = 3  # 爬虫深度
ITERATIONS = 20  # 计算PageRank的迭代次数


class Crawler:
    # 初始化Crawler类并传入数据库名称
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def db_commit(self):
        self.con.commit()

    # 辅助函数，用于获取条目的id，并且如果条目不存在，就将其加入到数据库中
    def get_entry_id(self, table, file_id, value, create_new=True):
        """
        返回条目的id，如果该条目不存在，程序会在数据库中新建一条记录
        :param table: 表名
        :param file_id: 字段名
        :param value: 值
        :param create_new: 是否新建记录
        :return: 条目的id
        """
        cur = self.con.execute(
            "select rowid from %s where %s='%s'" % (table, file_id, value)
        )
        res = cur.fetchone()
        if res is None:  # 数据库不存在该条记录，新增
            cur = self.con.execute(
                "insert into %s (%s) values ('%s')" % (table, file_id, value)
            )
            return cur.lastrowid
        else:
            return res[0]

    # 为每个网页建立索引
    def add_to_index(self, url, soup):
        """
        为网页建立索引
        首先获得一个网页中的单词列表，然后将网页及所有单词加入索引，在网页和单词之间建立关联，
        并保存单词在网页中出现的位置，即单词在列表中的索引号
        :param url:
        :param soup:
        :return:
        """
        if self.is_indexed(url):
            return
        print 'Indexing %s' % url

        # 获取每个单词
        text = self.get_text_only(soup)
        words = self.separte_words(text)

        # 得到url的id
        url_id = self.get_entry_id('urllist', 'url', url)

        # 将每个单词与该url关联
        for i in range(len(words)):
            word = words[i]
            if word in IGNORE_WORDS:
                continue
            word_id = self.get_entry_id('wordlist', 'word', word)
            self.con.execute('insert into wordlocation(urlid, wordid, location) values(%d, %d, %d)' %(url_id, word_id, i))

    # 从一个HTML网页中获取文字（不带标签的）
    def get_text_only(self, soup):
        """
        递归向下的方式获取网页中的文字，保留了文字出现的前后顺序
        :param soup: 含有标签的网页
        :return:网页中的文字
        """
        text = soup.string  # 只有一个子节点的时候，获取第该节点的内容，否则返回None
        if text is None:
            next_contents = soup.contents  # 返回该节点的子节点列表
            result_text = ''
            for content_item in next_contents:
                sub_text = self.get_text_only(content_item)
                result_text += sub_text + '\n'
            return result_text
        else:
            return text.strip()  # 移除字符串头尾指定的字符，默认为空格

    # 根据任何非空白字符进行分词处理
    def separte_words(self, text):
        """
        将字符串拆分成一组独立的单词
        :param text: 待拆分的字符串
        :return: 单词list
        """
        result_list = []
        splitter = re.compile(ur'[^a-zA-Z0-9_\u4e00-\u9fa5]')  # python2.7中要使用‘ur’匹配任意不是字母，数字，下划线，汉字的字符
        for s in splitter.split(text):  # 使用结巴分词，处理中文分词
            if s != '':
                result_list.extend(jieba.lcut(s.lower()))
        return result_list

    # 如果url已经建立索引，返回true
    def is_indexed(self, url):
        """
        判断网页是否存入数据库，如果存在 判断是否任何单词与之有关联
        :param url: 网页url
        :return:
        """
        urllist_rowid = self.con.execute(
            "select rowid from urllist where url='%s'" % url
        ).fetchone()
        if urllist_rowid is not None:  # 该网页已存入数据库
            # 检查是否已经被检索过,即是否有的单词与该网页有关联
            wordlocation_url = self.con.execute(
                "select * from wordlocation where urlid=%d" % urllist_rowid[0]
            ).fetchone()
            if wordlocation_url is not None:
                return True
        return False

    # 添加一个关联两个网页的链接
    def add_link_ref(self, url_from, url_to, link_text):
        """
        为两个网页添加链接
        :param url_from: 当前页面链接
        :param url_to: 关联到的链接
        :param link_text: 链接的文字
        :return:
        """
        # cur = self.con.execute(
        #     "select rowid from link where fromid='%s' and toid='%s' " % (url_from, url_to)
        # )
        # res = cur.fetchone()
        # if res is None:  # 数据库不存在该条记录，新增
        #     self.con.execute(
        #         "insert into link (fromid, toid) values ('%s', '%s')" % (url_from, url_to)
        #     )
        words = self.separte_words(link_text)
        fromid = self.get_entry_id('urllist', 'url', url_from)
        toid = self.get_entry_id('urllist', 'url', url_to)
        if fromid == toid:
            return
        cur = self.con.execute("insert into link(fromid,toid) values (%d,%d)" % (fromid, toid))
        linkid = cur.lastrowid
        for word in words:
            if word in IGNORE_WORDS:
                continue
            wordid = self.get_entry_id('wordlist', 'word', word)
            self.con.execute("insert into linkwords(linkid,wordid) values (%d,%d)" % (linkid, wordid))

    # 从一小组网页开始进行广度优先搜索，直至某一给定深度
    def crawl(self, pages, depth=CRAWLER_DEPTH):
        """
        循环遍历网页列表，针对每个网页调用add_to_index函数，添加索引。
        利用BeautifulSoup抓取网页中的所有链接，将这些链接添加到new_pages集合中
        一定深度循环结束之前，将new_page赋给pages,这一过程再次循环，知道depth结束
        :param pages:网页列表
        :param depth:循环深度
        :return:
        """
        for i in range(depth):
            new_pages = set()
            for page in pages:
                try:
                    url_response = urllib2.urlopen(page)
                except:
                    print 'Could not open %s' % page
                    continue
                soup = BeautifulSoup(url_response.read(), 'lxml')
                self.add_to_index(page, soup)

                links = soup.find_all('a')  # 找到所有超链接标签
                for link in links:
                    if 'href' in dict(link.attrs):  # 获取link的属性字典
                        url = urljoin(page, link['href'])  # 从相对路径获取绝对路径, page+相对路径地址
                        if url.find("'") != -1:  # 存在不合法字符
                            continue
                        url = url.split('#')[0]  # 去掉位置部分
                        if url[0:4] == 'http' and not self.is_indexed(url):
                            new_pages.add(url)
                        link_text = self.get_text_only(link)
                        self.add_link_ref(page, url, link_text)
                self.db_commit()
            pages = new_pages

    # 创建数据库表
    def create_index_tables(self):
        """
        为数据库的所有表建立schema，并建立一些只在加快搜索速度的索引
        :return:
        """
        self.con.execute('create table urllist(url)')
        self.con.execute('create table wordlist(word)')
        self.con.execute('create table wordlocation(urlid, wordid, location)')
        self.con.execute('create table link(fromid integer, toid integer)')
        self.con.execute('create table linkwords(wordid, linkid)')
        self.con.execute('create index wordidx on wordlist(word)')
        self.con.execute('create index urlidx on urllist(url)')
        self.con.execute('create index wordurlidx on wordlocation(wordid)')
        self.con.execute('create index urltoidx on link(toid)')
        self.con.execute('create index urlfromidx on link(fromid)')

    def calculate_page_rank(self, iterations=ITERATIONS):
        """
        预先为每个url计算PageRank值，并将结果存入数据表中，每次执行期间重新计算所有PageRank值
        最初将每个网页的PageRank值设置为1.0，然后遍历每个url，并针对每个外部回指链接，得到其PageRank值与链接总数
        :param iterations: 迭代次数
        :return:
        """
        # 清除当前的PageRank表
        self.con.execute('drop table if exists pagerank')
        self.con.execute('create table pagerank(urlid primary key, score)')

        # 初始化每个url，令其PageRank值为1
        self.con.execute('insert into pagerank select rowid, 1.0 from urllist')
        self.db_commit()

        for i in range(iterations):
            print "Iteration %d" % i
            for (url_id,) in self.con.execute('select rowid from urllist'):
                pr = 0.15

                # 循环遍历指向当前网页的所有网页
                for (linker,) in self.con.execute('select distinct fromid from link where toid=%d' % url_id):
                    # 得到链接源对应网页的PageRank值
                    linking_pr = self.con.execute('select score from pagerank where urlid=%d' % linker).fetchone()[0]

                    # 根据链接源，求得总的连接数
                    linking_count = self.con.execute('select count(*) from link where fromid=%d' % linker).fetchone()[0]
                    pr += 0.85*(linking_pr/linking_count)  # 回指链接的计算公式
                self.con.execute('update pagerank set score=%f where urlid=%d' % (pr, url_id))
            self.db_commit()


class Searcher:
    def __init__(self, db_name):
        self.con = sqlite.connect(db_name)

    def __del__(self):
        self.con.close()

    def normalize_scores(self, scores, small_is_better=0):
        """
        归一化函数，接受一个包含ID与评价值的字典，返回一个带有相同ID，而评价值介于0和1之间的新字典
        函数根据每个评价值与最佳结果的接近程度（最佳结果的对应值为1），对其进行相应的缩放处理
        :param scores: 包含ID和评价值的字典
        :param small_is_better:
        :return:
        """
        very_small = 0.00001  # 避免被0整除
        if small_is_better:
            min_score = min(scores.values())
            return dict([(u, float(min_score)/max(very_small, l))
                         for (u, l) in scores.items()])
        else:
            max_score = max(scores.values())
            if max_score == 0:
                max_score = very_small
            return dict([(u, float(c)/max_score)
                             for (u, c) in scores.items()])

    def get_match_rows(self, q):
        """
        查询函数，接受一个查询字符串，将其拆分成多个单词，构造SQL查询
        :param q:查询字符串
        :return:元祖(单词所在urlid(所有查询的单词出现在同一个url中), 单词1在网页的位置，单词2在网页的位置...), 单词所在位置id
        """
        # 构造查询的字符串
        field_list = 'w0.urlid'
        table_list = ''
        clause_list = ''
        word_ids = []

        # 根据空格拆分单词
        words = q.split(' ')
        table_number = 0

        for word in words:
            # 获取单词的ID
            word_row = self.con.execute(
                "select rowid from wordlist where word = '%s'" % word
            ).fetchone()
            if word_row is not None:
                word_id = word_row[0]
                word_ids.append(word_id)  # 存放单词id
                if table_number > 0:
                    table_list += ','
                    clause_list += ' and '
                    clause_list += 'w%d.urlid=w%d.urlid and ' % (table_number-1, table_number)
                field_list += ',w%d.location' % table_number
                table_list += 'wordlocation w%d' % table_number
                clause_list += 'w%d.wordid=%d' % (table_number, word_id)
                table_number += 1
        # 根据各个组分，建立查询
        full_query = 'select %s from %s where %s' % (field_list, table_list, clause_list)
        cur = self.con.execute(full_query)
        url_locations = [row for row in cur]  # 元祖

        return url_locations, word_ids

    def get_scored_list(self, url_locations, word_ids):
        """
        接受查询请求，将获取到的行集置于字典中，并以格式化列表的形式显示输出
        :param url_locations:
        :param word_ids:
        :return:
        """
        total_scores = dict([(row[0], 0) for row in url_locations])  # 键：单词所在url的id，值：0

        weights = [(1.0, self.frequency_score(url_locations)),
                   (1.0, self.location_score(url_locations)),
                   (1.0, self.page_rank_score(url_locations)),
                   (1.0, self.link_text_score(url_locations, word_ids))]
        for (weight, scores) in weights:
            for url in total_scores:
                total_scores[url] += weight*scores[url]
        return total_scores

    def get_url_name(self, id):
        """
        通过url的id查询url的名称
        :param id:url的id
        :return:url 名称
        """
        return self.con.execute(
            "select url from urllist where rowid=%d" % id
        ).fetchone()[0]

    def query(self, q):
        """
        查询多字符
        :param q:待查询字符串
        :return:查询结果，评分 url
        """
        url_locations, word_ids = self.get_match_rows(q)  # 获得单词的位置和url 查询结果
        scores = self.get_scored_list(url_locations, word_ids)
        ranked_scores = sorted([(score, url_id) for (url_id, score) in scores.items()], reverse=1)
        for (score, url_id) in ranked_scores[0:10]:
            print '%f\t%s' % (score, self.get_url_name(url_id))

    def frequency_score(self, rows):
        """
        单词频度度量函数，根据查询条件中的单词在网页中出现的次数对网页进行评价
        :param rows:行集，每一行的第一项是urlid，后面紧跟的是各待查找单词的位置信息
        :return:
        """
        counts = dict([(row[0], 0) for row in rows])
        for row in rows:
            counts[row[0]] += 1
        return self.normalize_scores(counts)

    def location_score(self, rows):
        """
        文档位置度量函数，搜索单词在网页中的出现位置
        一个网页与待搜索单词相关，则该单词更有可能靠近网页开始处，
        所以对待查找单词在文档中出现的越早给予越高的评价值
        :param rows:行集，每一行的第一项是urlid，后面紧跟的是各待查找单词的位置信息
        :return:
        """
        locations = dict([(row[0], 1000000) for row in rows])
        for row in rows:
            loc = sum(row[1:])  # 计算每一行 所有单词的位置之和
            if loc < locations[row[0]]:  # 与最佳结果对比，取更小者
                locations[row[0]] = loc
        return self.normalize_scores(locations, small_is_better=1)

    def distance_score(self, rows):
        """
        单词距离度量函数
        :param rows:
        :return:
        """
        # 如果最多只有两个单词，得分都一样
        if len(rows[0]) <= 2:
            return dict([(row[0], 1.0) for row in rows])

        # 初始化字典，并填入一个很大的数
        min_distance = dict([(row[0], 1000000) for row in rows])
        for row in rows:
            # 计算每一位置与上一个位置间的差距，找出距离最小者
            dist = sum([abs(row[i]-row[i-1]) for i in range(2, len(row))])
            if dist < min_distance[row[0]]:
                min_distance[row[0]] = dist
            return self.normalize_scores(min_distance, small_is_better=1)

    def inbound_link_score(self, rows):
        """
        简单计数，处理外部回指链接
        :param rows: 行集
        :return: 归一化处理后的评价结果，外部回指链接数
        """
        unique_urls = set([row[0] for row in rows])
        inbound_count = dict([(u, self.con.execute(
            'select count(*) from link where toid=%d' % u
        ).fetchone()[0]) for u in unique_urls])
        return self.normalize_scores(inbound_count)

    def page_rank_score(self, rows):
        """
        PageRank评价函数
        :param rows:
        :return:
        """
        page_ranks = dict([(row[0], self.con.execute('select score from pagerank where urlid=%d' % row[0]).fetchone()[0])
                           for row in rows])
        max_rank = max(page_ranks.values())
        normalized_scores = dict([(u, float(1)/max_rank) for (u, l) in page_ranks.items()])  # 归一化处理
        return normalized_scores

    def link_text_score(self, rows, word_ids):
        """
        利用链接文本排名
        循环遍历word_ids中的单词，并查找包含这些单词的链接。
        如果连接的目标地址与搜索结果中的某一条数据匹配，则链接源对应的PageRank值将会被加入到目标网页的最终评价值中
        :param rows: 行集
        :param word_ids: 单词ID列表
        :return:
        """
        link_scores = dict([(row[0], 0.00001) for row in rows])
        for word_id in word_ids:
            cur = self.con.execute('select link.fromid, link.toid from linkwords,link '
                                   'where wordid=%d and linkwords.linkid=link.rowid' % word_id)
            for (from_id, to_id) in cur:
                if to_id in link_scores:
                    pr = self.con.execute('select score from pagerank where urlid=%d' % from_id).fetchone()[0]
                    link_scores[to_id] += pr
        max_score = max(link_scores.values())
        normalized_scores = dict([(u, float(1)/max_score) for (u, l) in link_scores.items()])
        return normalized_scores

# crawler_obj = Crawler('search_index.db')
# crawler_obj.create_index_tables()  # 首次运行程序，创建数据库表
# page_list = ['http://www.csdn.net']
# crawler_obj.crawl(page_list)  # 首次运行程序，抓取page_list中的网页
# crawler_obj.calculate_page_rank()  # 计算PageRank，只有在更新索引的时候才需要运行该函数

search_obj = Searcher('search_index.db')
search_obj.query('python')
