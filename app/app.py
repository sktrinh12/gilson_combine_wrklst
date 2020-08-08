from flask import Flask
from mongo_.views import mongo_bp
from elasticsearch_.views import elasticsearch_bp
import os


def create_app():
    app = Flask(__name__)

    if app.config['ENV'] == 'development':
        app.config['HOSTNAME'] = 'localhost'
    else:
        # bc plots are rendered client-side so have to use actual local host not
        # pseudo host (192.X.X.X) used by docker
        app.config['HOST_PLOT'] = os.getenv('HOST_PLOT')
        app.config['HOSTNAME'] = os.getenv('PSEUDO_IPADDR')
    print(f"current ip address: {app.config['HOSTNAME']}")
    config_type = app.config['ENV'][0].upper() + app.config['ENV'][1:]
    app.config.from_object(f"config.{config_type}Config")

    app.register_blueprint(mongo_bp)
    app.register_blueprint(elasticsearch_bp)

    print(f'\n**ENV is set to: {app.config["ENV"]}**\n')

    return app


if __name__ == "__main__":
    create_app().run(host='0.0.0.0', port=8003)
