from functions import *
import time
from db_classes import ElasticsearchConnection
from elasticsearch import exceptions
from oracle_ import oracle_
import sys


def prepare_row_data_ES(tsl_file_path, sw_loc, plt_loc, seq_nbr, current_time,
                        uvdata_file_dir, hostname, app_tsl_filepath):
    '''print out the current running row data from raw worklist file and then
    prepare for ES ingestion; RETURNS a dictionary'''

    # ntpath can handle both windows ntpath and unix posixpath
    tsl_file_name = path_leaf(tsl_file_path)
    projectid = tsl_file_name.split('_', 1)[0]
    # make copy of the real path passed from the post request
    real_tsl_filepath = tsl_file_path
    # get parent directory of the tsl file
    parent_dir = ntpath.basename(ntpath.dirname(tsl_file_path))

    tsl_file_path = os.path.join(
        app_tsl_filepath, parent_dir, tsl_file_name)
    print(f"new tsl file path: {tsl_file_path}")

    # get current row data
    current_row_list = read_tsl_file(tsl_file_path, sw_loc)
    current_row_dict = convert_to_dict(current_row_list)

    # get current uvdata csv file
    uvdata_file = get_current_uvdata_file(
        uvdata_file_dir, current_row_dict['SAMPLE_NAME'], current_time)

    print(f"current uvdata file: {uvdata_file}")

    assert current_row_dict['SAMPLE_WELL'] == str(sw_loc), \
        'sample well mis-match "{0}" does not equal "{1}"'.format(
            current_row_dict['SAMPLE_WELL'], sw_loc)

    assert current_row_dict['PLATE_POSITION'] == plt_loc, \
        'plate location mis-match "{0}" does not equal "{1}"'.format(
            current_row_dict['PLATE_POSITION'], plt_loc)

    try:
        # 2019 format
        df = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file))
        # field_names = get_field_names(df)
        channel_names = get_chnl_names(df)
        uvdata_dict = gen_data_dict(
            channel_names, sep_data_into_lists(df, channel_names))
        print('uvdata file is 2019 format')
    except pd.errors.ParserError:
        # handle parse error since a different gilson export script used after
        # 2019 which places each value in separate cell and combines xy value in
        # some cells; excludes last column for data since it is x-value
        print('uvdata file is 2020 format')

        dfmeta = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file),
                             nrows=25)
        valid_cols = check_pd_usecols(uvdata_file_dir, uvdata_file)
        dfdata = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file),
                             skiprows=27, header=None, usecols=valid_cols)
        channel_names = get_chnl_names(dfmeta)
        # convert first column to string since others have two values
        # in each cell; the solvent x-value and abs y-value
        # dfdata[0] = dfdata[0].astype(str)

        channel_names = channel_names + ['TIME']
        data_list = list()
        # split each value and convert back to float; and index every 10 values
        # to reduce sampling rate; splitting is done since some uvdata files
        # are tab separated within a cell (y and x value in one cell)
        for c in dfdata.columns:
            data_list.append(dfdata[c].apply(lambda x: str(x).split(
                '\t')[1] if '\t' in str(x) else x).astype(float).tolist()[::10])
        uvdata_dict = {ch: val for ch, val in zip(channel_names, data_list)}

    # combine two dictionaries (1) is from current row in tsl file; (2) other is xml
    # meta data;
    row_data_keys = ['FINISH_DATE',
                     'SEQ_NUM',
                     'PROJECT_ID',
                     'GILSON_NUMBER',
                     'SAMPLE_WELL',
                     'TSL_FILEPATH',
                     'UVDATA_FILE',
                     'UVDATA'
                     ]

    row_data_vals = [current_time,
                     str(int(float(seq_nbr))),
                     projectid,
                     hostname,
                     sw_loc,
                     real_tsl_filepath,
                     path_leaf(uvdata_file),
                     uvdata_dict
                     ]

    # make the partial dictionary
    row_data_dict = {k: v for k, v in zip(row_data_keys, row_data_vals)}
    # update the dictionary that was generated by looking at tsl row
    row_data_dict.update(current_row_dict)

    # re-assign the row dictionary with keys ordered by master list
    row_data_dict = sort_dictkeys(row_data_dict, True)
    return row_data_dict


def sort_dictkeys(dct, incl_uvdata=False):
    '''sort dictionary by keys'''
    # master column list order for sorting
    key_name_list = [
        'FINISH_DATE',
        'SEQ_NUM',
        'PROJECT_ID',
        'METHOD_NAME',
        'SAMPLE_NAME',
        'BARCODE',
        'PLATE_ID',
        'BROOKS_BARCODE',
        'SAMPLE_WELL',
        'PLATE_POSITION',
        'GILSON_NUMBER',
        'TSL_FILEPATH',
        'UVDATA_FILE',
    ]

    if incl_uvdata:
        key_name_list = key_name_list + ['UVDATA']

    dct_ = {k: dct[k] for k in key_name_list}
    return dct_


def check_pd_usecols(uvdata_file_dir, uvdata_file):
    '''iterate from 0 - 3 to see which columns are valid (have a value) to avoid parse errors'''
    use_cols_nbr = []
    for i in range(5):
        dfdata = pd.DataFrame()
        try:
            dfdata = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file),
                                 skiprows=27, nrows=1, header=None, usecols=[i])
            if not dfdata.empty:
                use_cols_nbr.append(i)
        except (pd.errors.ParserError, ValueError):
            pass

    print(f'valid uvdata colms for {uvdata_file}: {use_cols_nbr}')
    return use_cols_nbr


def sort_colnames_ES(output):
    '''sort list of dictionaries for logs.html'''
    sorted_output = []
    for i, d in enumerate(output):
        # sorted_output.append({kn: output[i][kn] for kn in key_name_list})
        sorted_output.append(sort_dictkeys(output[i]))
    return sorted_output


def get_index_length(host, index_name):
    with ElasticsearchConnection(host=host) as es:
        stmt = es.indices.stats(index_name)[
            '_all']['primaries']['docs']['count']
        return int(stmt)


# def upload_data_to_ES(host, index_name, sleep_time, row_data_dict):
def upload_data_to_ES(host, index_name, sleep_time, input_json, oracle_params):

    # timer to wait for TRILUTION to export raw UV data
    for i in range(sleep_time, 0, -1):
        if i % 5 == 0:
            print(f'sleeping ... {i} secs left ...')
        time.sleep(1)

    try:
        current_ts = datetime.strptime(
            input_json['FINISH_DATE'], "%m/%d/%Y %I:%M:%S %p")
    except ValueError as e:
        current_ts = datetime.strptime(
            input_json['FINISH_DATE'], "%Y-%b-%d %H:%M:%S")

    data = prepare_row_data_ES(input_json['TSL_FILEPATH'], input_json['SAMPLE_WELL'],
                               input_json['PLATE_POSITION'],
                               input_json['SEQ_NUM'],
                               current_ts,
                               input_json['UVDATA_FILE_DIR'],
                               input_json['GILSON_NUMBER'],
                               input_json['APP_TSL_FILEPATH'])

    print(f"the finish date is: {data['FINISH_DATE']}")

    check, cnt = query_ES_dup_projid(host,
                                     index_name, data['PROJECT_ID'], data['SAMPLE_NAME'])
    print(f"check duplicate project id: {data['PROJECT_ID']} - {check}")
    print(
        f"count for duplicates: {cnt} based on sample_name {data['SAMPLE_NAME']}")
    if check:
        data['PROJECT_ID'] = data['PROJECT_ID'] + f"_{cnt}"

    # initalise the ES return object (dict)
    res = {'result': 'empty', '_id': 'empty'}

    # upload to ES
    if data:
        print('uploading to ES database ...')
        with ElasticsearchConnection(host=host) as es:
            res = es.index(
                index=index_name,  # use ES default _id assignment
                refresh='wait_for',  # without this, ES lags and cannnot update quick enough
                body=data
            )
            # refresh
            es.indices.refresh(index=index_name)
            # ensure no pending tasks?
            while es.cluster.pending_tasks()['tasks']:
                pass

    print(f"result of ES upload: {res['result']}; _id: {res['_id']}")
    print("####################")
    print(f"current ES document count: {get_index_length(host,index_name)}")
    sys.stdout.flush()
    # upload missing fields to oracle without the uvdata
    # for oracle upload
    data_no_uvdata = {k: data[k] for k in data.keys() - {'UVDATA'}}
    oracle_.upload_ordb_rowdata(data_no_uvdata,
                                oracle_params['ORACLE_USER'],
                                oracle_params['ORACLE_PASS'],
                                oracle_params['ORACLE_HOST'],
                                oracle_params['ORACLE_PORT'],
                                oracle_params['ORACLE_SERVNAME'],
                                oracle_params['ORACLE_TABLENAME'],
                                )
    return data_no_uvdata


def query_ES_data(host, index_name, project_id, sample_well):
    with ElasticsearchConnection(host=host) as es:
        res = es.search(index=index_name,
                        body={
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "match": {
                                                "PROJECT_ID": project_id
                                            }
                                        },
                                        {
                                            "match": {
                                                "SAMPLE_WELL": sample_well
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
                                "excludes":  ["UVDATA"]
                            },
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "wildcard": {
                                                "PROJECT_ID": f"{project_id}*"
                                            }

                                        },
                                        {
                                            "match": {
                                                "SAMPLE_NAME": sample_name
                                            }
                                        }

                                    ]
                                }
                            }
                        }
                        )
    # return res['hits']['hits'][0]['_source']
    cnt = int(res['hits']['total']['value'])
    if cnt != 0:
        return True, cnt + 1
    else:
        return False, 0


def check_ES_proj_id(host, index_name, project_id):
    '''check if project id exists using wildcard search query and output the result'''
    try:
        with ElasticsearchConnection(host=host) as es:
            res = es.search(index=index_name, body={
                "_source": {
                    "excludes":  ["UVDATA"]
                },
                "size": 1000,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "wildcard": {
                                    "PROJECT_ID": f"{project_id}*"
                                }
                            },
                        ]
                    }
                },
                "sort": [
                    {
                        "FINISH_DATE": {
                            "order": "desc"
                        }
                    }
                ]
            }
            )
        output = res['hits']
        if int(output['total']['value']) > 0:
            return True, [r['_source'] for r in output['hits']]
        return False, None
    except exceptions.RequestError:
        return False, None


def query_ES_latest(host, index_name, n_latest):
    try:
        with ElasticsearchConnection(host=host) as es:
            res = es.search(index=index_name, body={
                "_source": {
                    "excludes": ["UVDATA"]
                },

                "query": {
                    "match_all": {}
                },
                "size": n_latest,
                "sort": [
                    {
                        "FINISH_DATE": {
                            "order": "desc"
                        }
                    }
                ]
            })
        return [r['_source'] for r in res['hits']['hits']]
    except exceptions.RequestError as e:
        return []
