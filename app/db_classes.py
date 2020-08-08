from pymongo import MongoClient
from elasticsearch import Elasticsearch


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
