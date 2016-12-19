# coding: utf-8
# author: luyf
# create date: 2016.12.08

from math import tanh
from pysqlite2 import dbapi2 as sqlite


def dtanh(y):
    return 1.0 - y*y


class Searchnet:
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def make_tables(self):
        """
        创建数据库表函数，表hiddennode存储隐藏层，
        wordhidden存储从单词层到隐藏层的网络节点的链接状况，hiddenurl存储从隐藏层到输出层的链接状况
        :return:
        """
        self.con.execute('create table hiddennode(create_key)')
        self.con.execute('create table wordhidden(fromid,toid,strength)')
        self.con.execute('create table hiddenurl(fromid,toid,strength)')
        self.con.commit()

    def get_strength(self, from_id, to_id, layer):
        """
        判断当前连接的强度
        链接不存在时，返回默认值，对于单词层到隐藏层，默认值-0.2；对于隐藏层到输出层，默认值0
        :param from_id: 输入连接
        :param to_id: 输出连接
        :param layer: 层标识，0表示单词层，其他为隐藏层，不需要表示第一层，即输入层，因为要查询的强度是从第二层存储的
        :return:
        """
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'
        result = self.con.execute('select strength from %s where fromid=%d and toid=%d' % (table, from_id, to_id)).fetchone()
        if result is None:
            if layer == 0:
                return -0.2
            if layer == 1:
                return 0
        return result[0]

    def set_strength(self, from_id, to_id, layer, strength):
        """
        判断链接是否存在，并利用新的强度值更新连接或创建连接
        :param from_id:
        :param to_id:
        :param layer:
        :param strength:
        :return:
        """
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'
        result = self.con.execute('select rowid from %s where fromid=%d and toid=%d' % (table, from_id, to_id)).fetchone()
        if result is None:
            self.con.execute('insert into %s(fromid,toid,strength) values (%d,%d,%f)' % (table, from_id, to_id, strength))
        else:
            rowid = result[0]
            self.con.execute('update %s set strength=%f where rowid=%d' % (table, strength, rowid))

    def generate_hidden_node(self, word_ids, urls):
        """
        在隐藏层新建节点，在单词与隐藏节点之间，以及查询节点与有查询结果返回的URL结果之间，建立具有默认权重的连接
        :param word_ids: 输入层单词
        :param urls: 输出层url
        :return:
        """
        if len(word_ids) > 3:  # 目前只支持两个单词？？？
            return None
        # 检查是否已经为这组单词建好了一个隐藏节点
        create_key = '_'.join(sorted([str(wi) for wi in word_ids]))
        result = self.con.execute("select rowid from hiddennode where create_key='%s'" % create_key).fetchone()

        # 如果没有，则建立之，建立字段 word1_word2
        if result is None:
            cur = self.con.execute("insert into hiddennode (create_key) values('%s')" % create_key)
            hidden_id = cur.lastrowid
            # 设置默认权重
            for word_id in word_ids:
                self.set_strength(word_id, hidden_id, 0, 1.0/len(word_ids))  # 新建连接的默认值为1.0/len(word_ids)
            for url_id in urls:
                self.set_strength(hidden_id, url_id, 1, 0.1)  # 新建连接的默认值为0.1
            self.con.commit()

    def get_all_hidden_ids(self, word_ids, url_ids):
        """
        查询数据库中节点与连接的信息，从隐藏层中找出与某项查询相关的所有节点
        这些节点必须关联与查询条件中的某个单词，或者关联与查询结果中的某个URL
        :param word_ids:
        :param url_ids:
        :return:
        """
        link_list = {}
        for wordid in word_ids:
            cur = self.con.execute('select toid from wordhidden where fromid=%d' % wordid)
            for row in cur:
                link_list[row[0]] = 1
        for urlid in url_ids:
            cur =self.con.execute('select fromid from hiddenurl where toid=%d' % urlid)
            for row in cur:
                link_list[row[0]] = 1
        return link_list.keys()

    def setup_network(self, word_ids, url_ids):
        """
        建立包括当前所有权重值在内的相应网络
        :param word_ids:
        :param url_ids:
        :return:
        """
        # 值列表
        self.word_ids = word_ids  # 单词输入层
        self.hidden_ids = self.get_all_hidden_ids(word_ids, url_ids)  # 隐藏层
        self.url_ids = url_ids  # url输出层

        # 节点输出
        self.ai = [1.0]*len(self.word_ids)
        self.ah = [1.0]*len(self.hidden_ids)
        self.ao = [1.0]*len(self.url_ids)

        # 建立权重矩阵
        self.weight_i = [[self.get_strength(wordid, hiddenid, 0)
                          for hiddenid in self.hidden_ids]
                         for wordid in word_ids]
        self.weight_o = [[self.get_strength(hiddenid, urlid, 1)
                          for urlid in url_ids]
                         for hiddenid in self.hidden_ids]

    def feed_forward(self):
        """
        前馈算法，接受一列输入，返回所有输出层节点的输出结果
        循环遍历所有位于隐藏层的节点，并将所有来自输入层的输出结果乘以连接强度后累加起来
        每个节点的输出等于所有输入之和进过tanh函数计算后的结果，这一结果将被传给输出层
        输出层处理过程类似，将上一层输出结果乘以强度值，然后应用tanh函数给出最终结果
        :return:
        """
        # 查询单词是仅有的输入
        for i in range(len(self.word_ids)):
            self.ai[i] = 1.0

        # 隐藏层节点的活跃程度
        for j in range(len(self.hidden_ids)):
            sum_result_1 = 0.0
            for i in range(len(self.word_ids)):
                sum_result_1 += self.ai[i] * self.weight_i[i][j]
            self.ah[j] = tanh(sum_result_1)

        # 输出层节点的活跃程度
        for k in range(len(self.url_ids)):
            sum_result_2 = 0.0
            for j in range(len(self.hidden_ids)):
                sum_result_2 += self.ah[j] * self.weight_o[j][k]
            self.ao[k] = tanh(sum_result_2)
        return self.ao[:]

    def get_result(self, word_ids, url_ids):
        """
        建立神经网络
        :param word_ids:
        :param url_ids:
        :return:
        """
        self.setup_network(word_ids, url_ids)
        return self.feed_forward()

    def back_propagate(self, targets, N=0.5):
        """
        反向传播训练
        :param targets:
        :param N:
        :return:
        """
        # 计算输出层的误差
        output_deltas = [0.0] * len(self.url_ids)
        for i in range(len(self.url_ids)):
            error = targets[i] - self.ao[i]
            output_deltas[i] = dtanh(self.ao[i]) * error

        # 计算隐藏层的误差
        hidden_deltas = [0.0] * len(self.hidden_ids)
        for j in range(len(self.hidden_ids)):
            error = 0.0
            for k in range(len(self.url_ids)):
                error += output_deltas[k] * self.weight_o[j][k]
            hidden_deltas[j] = dtanh(self.ah[j]) * error

        # 更新输出权重
        for j in range(len(self.hidden_ids)):
            for k in range((len(self.url_ids))):
                change = output_deltas[k] * self.ah[j]
                self.weight_o[j][k] += N * change

        # 更新输入权重
        for i in range(len(self.word_ids)):
            for j in range(len(self.hidden_ids)):
                change = hidden_deltas[j] * self.ai[i]
                self.weight_i[i][j] += N * change

    def train_query(self, word_ids, url_ids, selected_url):
        """

        :param word_ids:
        :param url_ids:
        :param selected_url:
        :return:
        """
        self.generate_hidden_node(word_ids, url_ids)
        self.setup_network(word_ids, url_ids)
        self.feed_forward()
        targets = [0.0] * len(url_ids)
        targets[url_ids.index(selected_url)] = 1.0
        self.back_propagate(targets)
        self.update_database()

    def update_database(self):
        """

        :return:
        """
        # 将值存入数据库
        for i in range(len(self.word_ids)):
            for j in range(len(self.hidden_ids)):
                self.set_strength(self.word_ids[i], self.hidden_ids[j], 0, self.weight_i[i][j])
        for j in range(len(self.hidden_ids)):
            for k in range(len(self.url_ids)):
                self.set_strength(self.hidden_ids[j], self.url_ids[k], 1, self.weight_o[j][k])
        self.con.commit()


my_net = Searchnet('nn.db')
# # my_net.make_tables()  # 第一次运行，创建数据库表
word_world, word_river, word_bank = 101, 102, 103
url_worldbank, url_river, url_earth = 201, 202, 203
# my_net.generate_hidden_node([word_world, word_bank], [url_worldbank, url_river, url_earth])
# for w in my_net.con.execute('select * from wordhidden'):
#     print w
# for u in my_net.con.execute('select * from hiddenurl'):
#     print u
my_net.train_query([word_world, word_bank], [url_worldbank, url_river, url_earth], url_worldbank)
print my_net.get_result([word_world, word_bank], [url_worldbank, url_river, url_earth])

all_urls = [url_worldbank, url_river, url_earth]
for i in range(30):
    my_net.train_query([word_world, word_bank], all_urls, url_worldbank)
    my_net.train_query([word_river, word_bank], all_urls, url_river)
    my_net.train_query([word_world], all_urls, url_earth)
print my_net.get_result([word_world, word_bank], all_urls)
print my_net.get_result([word_river, word_bank], all_urls)
print my_net.get_result([word_bank], all_urls)
