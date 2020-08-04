from functions import *
from flask import current_app as app
import sys
from db_classes import MongoDBConnection
from pymongo import DESCENDING
sys.path.insert(0, "..")

# when sending to rq-redis msg broker, it is outside the scope of the app so
# cannot abstract the config.py variables as in other functions that are
# self-contained; therefore used a mongdb class with context mgmt instead


def query_mgdb_latest(db_name):
    with MongoDBConnection(db_name) as db:
        collect_list = db.list_collection_names()
        # print(collect_list)
        collect_list = sorted(collect_list, key=lambda
                              x: sort_collection_by_suffix(x), reverse=True)
        print(collect_list)
        return db[collect_list[0]].find({}, {'uvdata': 0, '_id': 0}).sort([('_id', 1)])


def sort_collection_by_suffix(c_elm):
    pi_suffix_len = len(c_elm.split('_')[-1])
    if pi_suffix_len > 3:  # more than 100 re-runs of same project_id
        pi_suffix_len = 0  # default to zero so that it doesnt' have indexerror
        # since there are two '_' in the string
    begin_suffix = c_elm.rfind('.')+1
    if '_' not in c_elm[begin_suffix:len(c_elm)]:
        suffix = int(c_elm[begin_suffix])
        # print(f"no suffix: {c_elm[begin_suffix]} - {c_elm}; {suffix}")
    else:
        suffix = int(c_elm[begin_suffix:len(c_elm)][-pi_suffix_len])
        # print(
        #     f"suffix: {c_elm[begin_suffix:len(c_elm)][-pi_suffix_len]}; {suffix}")
    # print(suffix)
    return suffix


def filter_mgdb_data_proj_id(db_name, project_id):
    with MongoDBConnection(db_name) as db:
        project_id_list = [pi for pi in db.list_collection_names() if
                           re.search(fr'{project_id}.*', pi)]
        # print(project_id_list)
        project_id_list = sorted(project_id_list, key=lambda
                                 x: sort_collection_by_suffix(x), reverse=True)
        if project_id_list:
            # return list of pymongo cursors of all matching project ids
            data_list = list(db[pi].find({}, {'uvdata': 0, '_id':
                                              # 0}).sort([('_id', 1)]) for
                                              0}).sort([('time_stamp', DESCENDING)]) for
                             pi in project_id_list)

            # have to iterate over cursor; a generator of elements
            new_data_list = []
            for pycur in data_list:
                for item in pycur:
                    new_data_list.append(item)
            # print(new_data_list)

            return True, new_data_list
        else:
            return False, None


def repeat_cnt_proj_id(db_name, project_id):
    with MongoDBConnection(db_name) as db:
        repeats = [pi for pi in db.list_collection_names() if
                   re.search(fr'{project_id}.*', pi)]
    return len(repeats) + 1


def get_mongo_data(db_name, project_id, sample_well):
    with MongoDBConnection(db_name) as db:
        return db.worklist_collection[project_id].find({'sample_well': sample_well}, {"_id": 0})[0]


def check_bc_sw(db_name, row_data_dict):
    '''check if barcode and sample well already exists in the project id'''
    barcode = row_data_dict['barcode']
    sample_well = row_data_dict['sample_well']
    with MongoDBConnection(db_name) as db:
        result = db.worklist_collection[row_data_dict['project_id']].find({'barcode': barcode,
                                                                           'sample_well':
                                                                           sample_well}, {'uvdata': 0})
    if result:
        return True
    return False


# def check_distinct_proj_id(db_name, project_id):
#     '''Checks for already ran project id's in mongodb'''
#     with MongoDBConnection(db_name) as db:
#         return any([re.search(fr'{project_id}.*', cnames) for cnames in
#                     db.list_collection_names()])


def upload_mongodb(db_name, sleep_time, row_data_dict):
    # if there are repeats, concatenate a cnt value at the end of
    # collection
    if check_bc_sw(db_name, row_data_dict):
        cnt = repeat_cnt_proj_id(db_name, row_data_dict['project_id'])
        with MongoDBConnection(db_name) as db:
            collection = db.worklist_collection[f"{row_data_dict['project_id']}_{cnt}"]
        # tag _cnt to the project id as well
        row_data_dict['project_id'] = row_data_dict['project_id'] + f"_{cnt}"
    else:
        with MongoDBConnection(db_name) as db:
            collection = db.worklist_collection[row_data_dict['project_id']]

    for i in range(sleep_time, 0, -1):
        if i % 10 == 0:
            print(f'sleeping ... {i} secs left ...')
        time.sleep(1)
    print()
    print('uploading to mongo database')
    return collection.insert_one(row_data_dict).inserted_id
