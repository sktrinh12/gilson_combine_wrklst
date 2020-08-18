from pymongo import MongoClient
from elasticsearch import Elasticsearch
import cx_Oracle


class MongoDBConnection(object):
    def __init__(self, host, db_name, port=27017):
        self.host = host
        self.port = port
        self.db_name = db_name
        self.client = None
        self.connection = None

    def __enter__(self):
        self.client = MongoClient(f"mongodb://{self.host}:{self.port}")
        self.connection = self.client[self.db_name]
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()


class ElasticsearchConnection(object):
    """Elasticsearch Connection"""

    def __init__(self, host, port=9200):
        self.host = host
        self.port = port
        self.connection = None

    def __enter__(self):
        self.connection = Elasticsearch(hosts=self.host, port=self.port)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()


class OracleConnection(object):
    """Oracle DB Connection"""

    def __init__(self, username, password, hostname, port, servicename):
        self.username = username
        self.password = password
        self.hostname = hostname
        self.port = port
        self.servicename = servicename
        self.con = None
        # self.cursor = None

    def __enter__(self):
        try:
            self.con = cx_Oracle.connect(
                self.username, self.password, f"{ self.hostname }:{ self.port }/{ self.servicename }")
            return self.con
        except cx_Oracle.DatabaseError as e:
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.con.close()
        except cx_Oracle.DatabaseError:
            pass

    # def execute(self, sql, bindvars=None, commit=False):
    #     """
    #     Execute whatever SQL statements are passed to the method;
    #     commit if specified.
    #     """
    #     try:
    #         self.cursor.execute(sql, bindvars)
    #     except cx_Oracle.DatabaseError as e:
    #         print(
    #             f'error inserting row data into Oracle database: {bindvars}')
    #         raise

    #     if commit:
    #         self.con.commit()
