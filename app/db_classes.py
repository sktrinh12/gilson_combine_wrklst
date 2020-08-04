from pymongo import MongoClient
from elasticsearch import Elasticsearch


class MongoDBConnection(object):
    """MongoDB Connection"""

    def __init__(self, db_name, host='localhost', port=27017):
        self.host = host
        self.port = port
        self.db_name = db_name
        self.connection = None
        self.connect_collection = None

    def __enter__(self):
        self.connection = MongoClient(self.host, self.port)
        return self.connection[self.db_name]

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()


class ElasticsearchConnection(object):
    """Elasticsearch Connection"""

    def __init__(self, host='localhost', port=9200):
        self.host = host
        self.port = port
        self.connection = None

    def __enter__(self):
        self.connection = Elasticsearch(hosts=self.host, port=self.port)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()
