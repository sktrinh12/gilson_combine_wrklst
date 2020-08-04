from flask import Flask
from mongo_.views import mongo_bp
from elasticsearch_.views import elasticsearch_bp
from oracle_.views import oracle_bp
import cx_Oracle
from pymongo import MongoClient
from worker import conn
from rq import Queue
from rq.job import Job
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)

    if app.config["ENV"] == "production":
        app.config.from_object("config.ProductionConfig")
    else:
        app.config.from_object("config.DevelopmentConfig")

    app.oracle_dsn_tns = cx_Oracle.makedsn(app.config['ORACLE_HOST'],
                                           app.config['ORACLE_PORT'],
                                           service_name=app.config['ORACLE_SERVNAME']
                                           )

    app.q = Queue(connection=conn)
    app.register_blueprint(mongo_bp)
    app.register_blueprint(elasticsearch_bp)
    app.register_blueprint(oracle_bp)

    print(f'\n**ENV is set to: {app.config["ENV"]}**\n')
    print()
    print(app.url_map)
    print()

    return app


if __name__ == "__main__":
    create_app().run()
