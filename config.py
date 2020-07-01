class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = "npsg"

    DB_NAME = "db-name"
    DB_USERNAME = "npsg"
    DB_PASSWORD = "npsg"

    SESSION_COOKIE_SECURE = True

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    DEBUG = True

    DB_NAME = "db-name"
    DB_USERNAME = "npsg"
    DB_PASSWORD = "npsg"

    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    TESTING = True

    DB_NAME = "db-name"
    DB_USERNAME = "npsg"
    DB_PASSWORD = "npsg"

    SESSION_COOKIE_SECURE = False
