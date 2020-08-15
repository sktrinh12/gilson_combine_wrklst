import os


class Config(object):
    DEBUG = False
    TESTING = False


class ProductionConfig(Config):
    DEBUG = True
    SECRET_KEY = 'nothing'  # for flash messages

    ES_INDEX_NAME = 'GILSON_LOGS'

    REDIS_URL = os.getenv("REDIS_URL")

    MGDB_COLLECTION = 'worklist_collection'
    MGDB_DBNAME = 'gilson_logs'
    # MGDB_FP = 'file_path'
    MGDB_ROWDATA = 'row_data'
    MGDB_CONTR = 'mongodb'

    TSL_FILEPATH = '/usr/src/app/mnt/tsl_files'
    UVDATA_FILE_DIR = '/usr/src/app/mnt/uvdata_files'
    SLEEP_TIME = 60*5


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = 'nothing'  # for flash messages

    ES_INDEX_NAME = 'test'

    REDIS_URL = "redis://localhost:6379/0"

    MGDB_COLLECTION = 'worklist_collection'
    MGDB_DBNAME = 'gilson_logs'
    MGDB_VARLOG = 'var_logs'

    TSL_FILEPATH = '/Users/trinhsk/Documents/GitRepos/gilson_webapp/test_files'
    UVDATA_FILE_DIR = '/Users/trinhsk/Documents/GitRepos/gilson_webapp/test_files/'
    SLEEP_TIME = 10


class TestingConfig(Config):
    DEBUG = True
    SECRET_KEY = 'nothing'  # for flash messages

    ES_INDEX_NAME = 'test'

    REDIS_URL = os.getenv("REDIS_URL")

    MGDB_COLLECTION = 'worklist_collection'
    MGDB_DBNAME = 'gilson_logs'  # for plotting, storing each run; alternative to ES
    # MGDB_FP = 'file_path'
    MGDB_ROWDATA = 'row_data'  # collection name
    MGDB_CONTR = 'mongodb'  # host name

    TSL_FILEPATH = '/usr/src/app/mnt/tsl_files'
    UVDATA_FILE_DIR = '/usr/src/app/mnt/uvdata_files'
    # SLEEP_TIME = 60*4
    SLEEP_TIME = 4
    # JSON_SORT_KEYS = False  # prevent response from being sorted alphabetically
