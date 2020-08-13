from flask import (Blueprint, render_template, request,
                   flash, jsonify, current_app, redirect)
from elasticsearch_.elasticsearch_ import *
from worker import Connection, redis, Queue
from mongo_.mongo_ import *


elasticsearch_bp = Blueprint(
    'elasticsearch_bp', __name__, template_folder='templates', static_folder='static')


@elasticsearch_bp.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@elasticsearch_bp.route('/')
def blank_main():
    return render_template('elasticsearch_/index.html', output="",
                           switch_var='log')


@elasticsearch_bp.route('/es/')
def main():
    host = current_app.config['HOSTNAME']
    # query on server-side
    output = ""
    output = query_ES_latest(host, current_app.config['ES_INDEX_NAME'], 8)
    if output:
        output = sort_colnames_ES(output)

    # if it exists, assigned from app.py init, then use that for plot rendering;
    # query for client-side
    if current_app.config['HOST_PLOT']:
        host = current_app.config['HOST_PLOT']

    return render_template('elasticsearch_/index.html', output=output,
                           host=host, switch_var='log')


@elasticsearch_bp.route('/es/show-current-data/<hostname>')
def show_current_data(hostname):
    # tsl_file_path = get_filepath_mgdb(hostname)
    # returns None if cannot find in mgdb
    current_row_data = get_latest_rowdata_mgdb(hostname)

    if current_row_data:
        tsl_file_path = current_row_data['TSL_FILEPATH']
        try:
            current_ts = datetime.strptime(
                current_row_data['FINISH_DATE'], "%m/%d/%Y %I:%M:%S %p")
        except ValueError as e:
            current_ts = datetime.strptime(
                current_row_data['FINISH_DATE'], "%Y-%b-%d %H:%M:%S")

        data = prepare_row_data_ES(tsl_file_path, current_row_data['SAMPLE_WELL'],
                                   current_row_data['PLATE_POSITION'],
                                   current_row_data['SEQ_NUM'],
                                   current_ts,
                                   current_app.config['UVDATA_FILE_DIR'], hostname)

        data = sort_dictkeys(data)
        # for k, v in data.items():
        #     print(k, v)

        return jsonify(data), 202

    return jsonify({'output': f'No data retrieved for {hostname}'})

# @elasticsearch_bp.route('/es/post/filepath/', methods=['POST'])
# def post_filepath_mongodb():
#     # force mimetype to be application/json
#     input_json = None
#     input_json = request.get_json(force=True)
#     if input_json:
#         print(f'data from client-side: {input_json}')
#         check = check_gilson_nbr(
#             app.config['MGDB_FP'], input_json["gilson_number"])
#         if not check:
#             # insert into tsl file path database
#             insert_mgdb(current_app.config['MGDB_FP'], input_json)
#             print(f'inserted new tsl file path - {input_json}')
#         else:
#             update_mgdb(current_app.config['MGDB_FP'], input_json)
#             print(f'updated new tsl file path - {input_json}')
#         return jsonify({'status': f'submitted to mongodb', input_json)


@elasticsearch_bp.route('/es/post/rowdata/', methods=['POST'])
def post_rowdata_mongodb():
    '''includes both filepath and the xml row data (combined into one post
    request)'''
    input_json = None
    # force mimetype to be application/json
    input_json = request.get_json(force=True)
    print(f'data from client-side: {input_json}')

    if input_json:
        # must remove empty fields that are requisite for NPSG endpoint
        # (gateway so that vlans can communicate to linux VM); dont upload empty
        # values into mgongodb
        for empty_keys in ["PROJECT_ID", "SAMPLE_NAME", "BARCODE",
                           "PLATE_ID", "BROOKS_BARCODE"]:
            try:
                input_json.pop(empty_keys)
            except KeyError:
                pass
        # insert row data (XML & filepath) to database
        insert_mgdb(current_app.config['MGDB_ROWDATA'], input_json)
        print(f'inserted new data row - {input_json}')
        # must remove '_id' key since it is not json serialisable
        input_json.pop('_id')

        print(f'current tsl file: {input_json["TSL_FILEPATH"]}')
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
                                   current_app.config['UVDATA_FILE_DIR'],
                                   input_json['GILSON_NUMBER'])
        # for server response
        data_no_uvdata = {k: data[k] for k in data.keys() - {'UVDATA'}}

        # Send a job to the task queue
        # result_ttl - specifies how long (in seconds) successful jobs and their results are kept
        index_name = current_app.config['ES_INDEX_NAME']
        sleep_time = current_app.config['SLEEP_TIME']
        host = current_app.config['HOSTNAME']
        redis_url = current_app.config['REDIS_URL'].strip().replace('"', '')
        print(f'redis url from add-task endpoint: {redis_url}')

        check, cnt = query_ES_dup_projid(host,
                                         index_name, data['PROJECT_ID'], data['SAMPLE_NAME'])
        print(f'check duplicate project id: {check}')
        print(f'count for duplicates: {cnt}')
        if check:
            data['PROJECT_ID'] = data['PROJECT_ID'] + f"_{cnt}"

        with Connection(redis.from_url(redis_url)):
            q = Queue()
            task = q.enqueue(upload_data_to_ES, args=(host,
                                                      index_name,
                                                      sleep_time,
                                                      data), job_timeout=60*5, result_ttl=1000)
        q_len = len(q)  # Get the queue length
        enq_time = task.enqueued_at.strftime('%a, %d-%b-%Y %H:%M: %S')
        message = f"""Task {task.id} queued at {enq_time}; len: {q_len} jobs queued"""
        # return jsonify({'output': message, 'data': input_json}), 202
        return jsonify({'output': message, 'data': data_no_uvdata}), 202
    return jsonify({'status': f'error'})


@ elasticsearch_bp.route('/es/get/rowdata/<gilson_number>', methods=['GET'])
def get_rowdata_mongodb(gilson_number):
    rowdata = get_latest_rowdata_mgdb(gilson_number)
    if rowdata:
        print(f'retrieved data row - {rowdata}')
        return jsonify({"output": rowdata})
    print(f'No data retrieved for most recent run from {gilson_number}')
    return jsonify({"output": "No data"})


# @ elasticsearch_bp.route('/es/get/tslfilepath/<gilson_number>', methods=['GET'])
# def get_tslfilepath_mongodb(gilson_number):
#     tsl_filepath = get_filepath_mgdb(gilson_number)
#     if tsl_filepath:
#         print(f'retrieved tsl file path- {tsl_filepath}')
#         return jsonify({"output": tsl_filepath})
#     print(f'No filepath retrieved for {gilson_number}')
#     return jsonify({"output": "No tsl filepath"})


@ elasticsearch_bp.route('/es/uvplot/<project_id>/<sample_well>')
def uvplot(project_id, sample_well):
    data_dict = query_ES_data(current_app.config['HOSTNAME'],
                              current_app.config['ES_INDEX_NAME'], project_id, sample_well)
    # print(f"brooks bc: {data_dict['brooks_bc']}")
    # for k, v in data_dict.items():
    #     print(k, v)
    plot = create_plot(data_dict)
    return render_template('elasticsearch_/plot.html', plot=plot, data_dict=data_dict)


@ elasticsearch_bp.route('/es/filter_proj_id', methods=["POST"])
def filter_proj_id():
    if request.method == "POST":
        result = None
        host = current_app.config['HOSTNAME']
        input_proj_id = request.form['filter']
        result, output = check_ES_proj_id(host,
                                          current_app.config['ES_INDEX_NAME'], input_proj_id)

        if not input_proj_id:
            # handle when not input; but click submit button
            msg = 'No project ID entered'
            print(msg)
            flash(msg, 'warning')
            return redirect('/')
        if result:
            print(output)
            output = sort_colnames_ES(output)
            if current_app.config['HOST_PLOT']:
                host = current_app.config['HOST_PLOT']
            return render_template('elasticsearch_/index.html', output=output,
                                   host=host, switch_var='log')
        else:
            msg = 'That project id does not exist'
            print(msg)
            flash(msg, 'warning')
            return redirect('/')

    return redirect('/')


@ elasticsearch_bp.route('/es/task-results/<task_id>', methods=['GET'])
def get_task_results(task_id):
    task = None
    redis_url = current_app.config['REDIS_URL'].strip().replace('"', '')
    with Connection(redis.from_url(redis_url)):
        q = Queue()
        task = q.fetch_job(task_id)
    if task:
        res_dict = {"data": {
            "task_id": task.get_id(),
            "task_function": task.func_name,
            "task_exc_info": task.exc_info,
            "task_enqueue_time": task.enqueued_at,
            "task_start_time": task.started_at,
            "task_end_time": task.ended_at,
            "task_result": task.result,
            "task_status": task.get_status()
        },
        }
    else:
        res_dict = {
            'status': f"Couldn't fetch that job ID - task_id: {task_id}; perhaps it does not exist!"}
    return jsonify(res_dict), 202


# @ elasticsearch_bp.route("/es/add-task/<hostname>")
# def add_task(hostname):
#     current_row_data = get_latest_rowdata_mgdb(hostname)
#     tsl_file_path = current_row_data['TSL_FILEPATH']

#     print(f'current tsl file: {tsl_file_path}')
#     try:
#         current_ts = datetime.strptime(
#             current_row_data['FINISH_DATE'], "%m/%d/%Y %I:%M:%S %p")
#     except ValueError as e:
#         current_ts = datetime.strptime(
#             current_row_data['FINISH_DATE'], "%Y-%b-%d %H:%M:%S")

#     data = prepare_row_data_ES(tsl_file_path, current_row_data['SAMPLE_WELL'],
#                                current_row_data['PLATE_POSITION'],
#                                current_ts,
#                                current_app.config['UVDATA_FILE_DIR'], hostname)

#     # Send a job to the task queue
#     # result_ttl - specifies how long (in seconds) successful jobs and their results are kept
#     index_name = current_app.config['ES_INDEX_NAME']
#     sleep_time = current_app.config['SLEEP_TIME']
#     host = current_app.config['HOSTNAME']
#     redis_url = current_app.config['REDIS_URL'].strip().replace('"', '')
#     print(f'redis url from add-task endpoint: {redis_url}')

#     check, cnt = query_ES_dup_projid(host,
#                                      index_name, data['project_id'], data['sample_name'])
#     print(f'check duplicate project id: {check}')
#     print(f'count for duplicates: {cnt}')
#     if check:
#         data['project_id'] = data['project_id'] + f"_{cnt}"
#     with Connection(redis.from_url(redis_url)):
#         q = Queue()
#         task = q.enqueue(upload_data_to_ES, args=(host,
#                                                   index_name,
#                                                   sleep_time,
#                                                   data), job_timeout=150, result_ttl=1000)
#     q_len = len(q)  # Get the queue length
#     enq_time = task.enqueued_at.strftime('%a, %d-%b-%Y %H:%M: %S')
#     message = f"""Task {task.id} queued at {enq_time}; len: {q_len} jobs queued"""
#     return jsonify({'output': message}), 202


@ elasticsearch_bp.route("/es/form-combine-worklists")
def form_combine_worklists():
    '''bare html for redirecting if there was an issue with the submission'''
    return render_template('elasticsearch_/combine_worklists.html',
                           switch_var='wl', title='')


@ elasticsearch_bp.route("/es/combine-worklists", methods=['POST'])
def combine_worklists():
    '''calls functions to combine two worklists based on the input entered in
    the form'''

    comb_df = pd.DataFrame()
    # grab from ajax function in app.js
    # input_rack_id1 = request.args.get('input_rack_id1')
    input_rack_id1 = request.form['rack1']
    input_rack_id2 = request.form['rack2']
    print(f'rack1 id: {input_rack_id1}')
    # input_rack_id2 = request.args.get('input_rack_id2')
    print(f'rack2 id: {input_rack_id2}')

    if not input_rack_id1 or not input_rack_id2:
        msg = 'Missing rack IDs'
        # return jsonify(dict(row_data=msg))
        print(msg)
        flash(msg, 'warning')
        return redirect('/es/form-combine-worklists')

    tsl_filepath = os.path.join(
        current_app.config['TSL_FILEPATH'], 'Sample List_tsl')

    dct_df = srchmap_tslfile_dictdf([input_rack_id1, input_rack_id2],
                                    tsl_filepath)

    n_drive = "N:\\npsg\\tecan\SourceData\\SecondStage\\Sample List_Combined_tmp"

    if len(dct_df) < 2 or not dct_df:
        msg = f"Couldn't find one/both TSL file(s); check if the rack ID entered is correct or make sure the TSL file(s) is/are in {n_drive}"
        print(msg)
        flash(msg, 'warning')
        return redirect('/es/form-combine-worklists')

    try:
        comb_df = main_combine_worklists(dct_df[input_rack_id1],
                                         dct_df[input_rack_id2])
        # print(comb_df)
        if not comb_df.empty:
            # index columns so that the table is shorter in width
            comb_df_for_html = comb_df.iloc[:, [1, 2, 4, 9, 10, 11]]
            # add sequence number
            comb_df_for_html['seq_nbr'] = [
                i+1 for i in comb_df_for_html.index.tolist()]
            # re-order columns
            cols = comb_df_for_html.columns.tolist()
            cols = cols[-1:] + cols[:-1]
            comb_df_for_html = comb_df_for_html[cols]
            # add css class name for group colouring
            cls_name = comb_df['colour_css_cls'].values.tolist()
            cls_name = ['none' if pd.isna(x) else x for x in cls_name]
            # write to file without the table colour group css class
            dfcsv = comb_df.iloc[:, [*range(comb_df.shape[1]-1)]]
            fn = f"{input_rack_id1[:8]}_{input_rack_id1[-3:]}_{input_rack_id2[-3:]}_comb.tsl"
            # dfcsv.replace({r'\r\n': ''}, regex=True, inplace=True)
            dfcsv.to_csv(os.path.join(
                current_app.config['TSL_FILEPATH'], 'Sample List_Combined_tmp',
                fn), sep='\t', index=False)
            msg = f'file path of tsl file: {n_drive}\\{fn}'
            print(msg)
            flash(msg, 'info')

            return render_template('elasticsearch_/combine_worklists.html',
                                   row_data=list(
                                       comb_df_for_html.values.tolist()),
                                   columns=['SEQ NUMBER', 'METHOD NAME', 'SAMPLE NAME',
                                            'DESCRIPTION', 'NOTES',
                                            'SAMPLE WELL', 'PLATE SAMPLE'],
                                   cls_name=cls_name,
                                   title=f'Simplified version of the combined TSL file: {input_rack_id1} and {input_rack_id2}')
    except Exception as e:
        msg = f"An error occured combing the tsl files - {e}"
        # return jsonify(dict(row_data=msg, columns=""))
        print(msg)
        flash(msg, 'warning')
        return redirect('/es/form-combine-worklists')


@ elasticsearch_bp.route("/es/logs")
def show_logs():
    '''bare html file for including into index.html or for ajax injection'''
    host = current_app.config['HOSTNAME']
    # query on server-side
    output = query_ES_latest(host, current_app.config['ES_INDEX_NAME'], 8)
    if output:
        output = sort_colnames_ES(output)
    # else:
    #     notes = 'Empty ES index - {current_app.config["ES_INDEX_NAME"]}'
    #     print(notes)

    if current_app.config['HOST_PLOT']:
        host = current_app.config['HOST_PLOT']
    return render_template('elasticsearch_/logs.html', output=output, host=host,
                           switch_var='log')
