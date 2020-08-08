from functions import *
import time
from flask import current_app as app
from db_classes import ElasticsearchConnection
from elasticsearch import exceptions


def prepare_row_data_ES(tsl_file_path, sw_loc, plt_loc, current_time, uvdata_file_dir, hostname):
    '''print out the current running row data from raw worklist file and then repare for sql entry
       RETURNS a dictionary'''
    # ntpath can handle both windows ntpath and unix posixpath

    tsl_file_name = path_leaf(tsl_file_path)
    projectid = tsl_file_name.split('_', 1)[0]

    tsl_file_path = os.path.join(app.config['TSL_FILEPATH'], tsl_file_name)
    print(f"new tsl file path: {tsl_file_path}")

    # get current row data
    current_row_list = read_tsl_file(tsl_file_path, sw_loc)
    current_row_dict = convert_to_dict(current_row_list)

    # get current uvdata csv file
    uvdata_file = get_current_uvdata_file(
        uvdata_file_dir, current_row_dict['sample_name'], current_time)

    assert current_row_dict['sample_well'] == str(sw_loc), \
        'sample well mis-match "{0}" does not equal "{1}"'.format(
            current_row_dict['sample_well'], sw_loc)

    # assert current_row_dict['notes'] == notes\
    #    'notes mis-match "{0}" does not equal "{1}"'.format(current_row_dict['notes'], notes)

    assert current_row_dict['plate_loc'] == plt_loc, \
        'plate location mis-match "{0}" does not equal "{1}"'.format(
            current_row_dict['plate_loc'], plt_loc)

    # assert current_row_dict['sample_name'] == sample_name, \
    #     'sample name mis-match "{0}" does not equal "{1}"'.format(
    #         current_row_dict['sample_name'], sample_name)

    try:
        # 2019 format
        df = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file))
        field_names = get_field_names(df)
        channel_names = get_chnl_names(df)
        uvdata_dict = gen_data_dict(
            channel_names, sep_data_into_lists(df, channel_names))
    except pd.errors.ParserError:
        # handle parse error since a different gilson export script used after
        # 2019 which places each value in separate cell and combines xy value in
        # some cells; excludes last column for data since it is x-value
        dfmeta = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file),
                             nrows=25)
        dfdata = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file),
                             skiprows=27, header=None, usecols=[0, 1, 2, 3])
        field_names = get_field_names(dfmeta)
        channel_names = get_chnl_names(dfmeta)
        # convert first column to string since others have two values
        # in each cell; the solvent x-value and abs y-value
        dfdata[0] = dfdata[0].astype(str)
        data_list = list()
        # split each value and convert back to float; and index every 10 values
        # to reduce sampling rate
        for c in dfdata.columns:
            data_list.append(dfdata[c].apply(lambda x: x.split(
                '\t')[1] if '\t' in x else x).astype(float).tolist()[::10])
        uvdata_dict = {ch: val for ch, val in zip(channel_names, data_list)}

    row_data_keys = ['time_stamp',
                     'project_id',
                     'gilson_number',
                     'sample_well',
                     'tsl_file',
                     'uvdata_file',
                     'uvdata'
                     ]

    row_data_vals = [current_time,
                     projectid,
                     hostname,
                     sw_loc,
                     tsl_file_name,
                     path_leaf(uvdata_file),
                     uvdata_dict
                     ]

    # make the partial dictionary
    row_data_dict = {k: v for k, v in zip(row_data_keys, row_data_vals)}
    row_data_dict.update(current_row_dict)

    return row_data_dict


def sort_colnames_ES(output):
    # master column list order for sorting
    key_name_list = ['time_stamp',
                     'project_id',
                     'gilson_number',
                     'method_name',
                     'sample_name',
                     'barcode',
                     'brooks_bc',
                     'id_suffix',
                     'sample_well',
                     'plate_loc',
                     'tsl_file',
                     'uvdata_file',
                     ]

    sorted_output = []
    for i, d in enumerate(output):
        sorted_output.append({kn: output[i][kn] for kn in key_name_list})
    return sorted_output


def get_index_length(host, index_name):
    with ElasticsearchConnection(host=host) as es:
        stmt = es.indices.stats(index_name)[
            '_all']['primaries']['docs']['count']
        return int(stmt)


def upload_data_to_ES(host, index_name, sleep_time, row_data_dict):
    # idx_adder = get_index_length(index_name)
    # print(f"_id of newly added data: {idx_adder+1}")
    res = {'result': 'empty', '_id': 'empty'}
    for i in range(sleep_time, 0, -1):
        if i % 5 == 0:
            print(f'sleeping ... {i} secs left ...')
        time.sleep(1)
    print()
    if row_data_dict:
        print('uploading to ES database ...')
        with ElasticsearchConnection(host=host) as es:
            res = es.index(
                index=index_name,  # use ES default _id assignment
                refresh='wait_for',  # without this, ES lags and cannnot update quick enough
                body=row_data_dict
            )
            # refresh
            es.indices.refresh(index=index_name)
            # ensure no pending tasks?
            while es.cluster.pending_tasks()['tasks']:
                pass

    print(f"result of upload: {res['result']}; _id: {res['_id']}")
    print()
    print(f"current document count: {get_index_length(host,index_name)}")


def query_ES_data(host, index_name, project_id, sample_well):
    with ElasticsearchConnection(host=host) as es:
        res = es.search(index=index_name,
                        body={
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "match": {
                                                "project_id": project_id
                                            }
                                        },
                                        {
                                            "match": {
                                                "sample_well": sample_well
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                        )
    if res:
        return res['hits']['hits'][0]['_source']
    else:
        return None


def query_ES_dup_projid(host, index_name, project_id, sample_name):
    with ElasticsearchConnection(host=host) as es:
        res = es.search(index=index_name,
                        body={
                            "_source": {
                                "excludes":  "uvdata"
                            },
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "wildcard": {
                                                "project_id": f"{project_id}*"
                                            }

                                        },
                                        {
                                            "match": {
                                                "sample_name": sample_name
                                            }
                                        }

                                    ]
                                }
                            }
                        }
                        )
    # return res['hits']['hits'][0]['_source']
    cnt = int(res['hits']['total']['value'])
    if cnt > 1:
        return True, cnt + 1
    else:
        return False, 0


def check_ES_proj_id(host, index_name, project_id):
    '''check if project id exists using wildcard search query and output the result'''
    with ElasticsearchConnection(host=host) as es:
        res = es.search(index=index_name, body={
            "_source": {
                        "excludes":  "uvdata"
                        },
            "query": {
                "bool": {
                    "must": [
                        {
                            "wildcard": {
                                "project_id": f"{project_id}*"
                            }
                        },
                    ]
                }
            }
        }
        )
    output = res['hits']
    if int(output['total']['value']) > 0:
        return True, [r['_source'] for r in output['hits']]
    return False, None


def query_ES_latest(host, index_name, n_latest):
    try:
        with ElasticsearchConnection(host=host) as es:
            res = es.search(index=index_name, body={
                "_source": {
                    "excludes": ["uvdata"]
                },

                "query": {
                    "match_all": {}
                },
                "size": n_latest,
                "sort": [
                    {
                        "time_stamp": {
                            "order": "desc"
                        }
                    }
                ]
            })
        return [r['_source'] for r in res['hits']['hits']]
    except exceptions.RequestError as e:
        return []
