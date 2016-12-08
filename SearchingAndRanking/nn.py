# coding: utf-8
# author: luyf
# create date: 2016.12.08

from math import tanh
from pysqlite2 import dbapi2 as sqlite

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
