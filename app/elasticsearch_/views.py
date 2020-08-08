from flask import (Blueprint, render_template, request,
                   flash, jsonify, current_app)
from elasticsearch_.elasticsearch_ import *
from worker import Connection, redis, Queue
from mongo_.mongo_ import *


elasticsearch_bp = Blueprint(
    'elasticsearch_bp', __name__, template_folder='templates', static_folder='static')


@elasticsearch_bp.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@elasticsearch_bp.route('/')
@elasticsearch_bp.route('/es/index.html')
def main():
    host = current_app.config['HOSTNAME']
    # query on server-side
    output = query_ES_latest(host, current_app.config['ES_INDEX_NAME'], 8)
    if output:
        output = sort_colnames_ES(output)
        # print(output)
    else:
        notes = 'Empty ES index - {current_app.config["ES_INDEX_NAME"]}'
        print(notes)

    # if it exists, assigned from app.py init, then use that for plot rendering;
    # query for client-side
    if current_app.config['HOST_PLOT']:
        host = current_app.config['HOST_PLOT']

    return render_template('elasticsearch_/index.html', output=output, host=host, notes="")


@elasticsearch_bp.route('/es/show-current-data/<hostname>')
def show_current_data(hostname):
    tsl_file_path = get_filepath_mgdb(hostname)
    current_row_data = get_latest_rowdata_mgdb(hostname)
    try:
        current_ts = datetime.strptime(
            current_row_data['time'], "%m/%d/%Y %I:%M:%S %p")
    except ValueError as e:
        current_ts = datetime.strptime(
            current_row_data['time'], "%Y-%b-%d %H:%M:%S")

    # pass sample_name as well to assert
    data = prepare_row_data_ES(tsl_file_path, current_row_data['sample_well'],
                               current_row_data['plate_loc'],
                               current_ts,
                               current_app.config['UVDATA_FILE_DIR'], hostname)

    return jsonify(data), 202


@elasticsearch_bp.route('/es/post/filepath/', methods=['POST'])
def post_filepath_mongodb():
    # force mimetype to be application/json
    input_json = None
    input_json = request.get_json(force=True)
    if input_json:
        print(f'data from client-side: {input_json}')
        check = check_gilson_nbr(
            app.config['MGDB_FP'], input_json["gilson_number"])
        if not check:
            # insert into tsl file path database
            insert_mgdb(current_app.config['MGDB_FP'], input_json)
            print(f'inserted new tsl file path - {input_json}')
        else:
            update_mgdb(current_app.config['MGDB_FP'], input_json)
            print(f'updated new tsl file path - {input_json}')
        return jsonify({'status': f'submitted to mongodb : {input_json}'})


@elasticsearch_bp.route('/es/post/rowdata/', methods=['POST'])
def post_rowdata_mongodb():
    input_json = request.get_json(force=True)
    if input_json:
        print(f'data from client-side: {input_json}')
        # insert into row data (XML) database
        insert_mgdb(current_app.config['MGDB_ROWDATA'], input_json)
        print(f'inserted new data row - {input_json}')
        return jsonify({'status': f'submitted to mongodb : {input_json}'})


@elasticsearch_bp.route('/es/get/rowdata/<gilson_number>', methods=['GET'])
def get_rowdata_mongodb(gilson_number):
    rowdata = get_latest_rowdata_mgdb(gilson_number)
    if rowdata:
        print(f'retrieved data row - {rowdata}')
        return jsonify({"output": rowdata})
    print(f'No data retrieved for most recent run from {gilson_number}')
    return jsonify({"output": "No data"})


@elasticsearch_bp.route('/es/get/tslfilepath/<gilson_number>', methods=['GET'])
def get_tslfilepath_mongodb(gilson_number):
    tsl_filepath = get_filepath_mgdb(gilson_number)
    if tsl_filepath:
        print(f'retrieved tsl file path- {tsl_filepath}')
        return jsonify({"output": tsl_filepath})
    print(f'No filepath retrieved for {gilson_number}')
    return jsonify({"output": "No tsl filepath"})


@ elasticsearch_bp.route('/es/uvplot/<project_id>/<sample_well>')
def uvplot(project_id, sample_well):
    data_dict = query_ES_data(current_app.config['HOSTNAME'],
                              current_app.config['ES_INDEX_NAME'], project_id, sample_well)
    # print(f"brooks bc: {data_dict['brooks_bc']}")
    # for k, v in data_dict.items():
    #     print(k, v)
    plot = create_plot(data_dict)
    return render_template('elasticsearch_/plot.html', plot=plot, data_dict=data_dict)


@ elasticsearch_bp.route('/es/filter_proj_id', methods=["GET", "POST"])
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
            return render_template('elasticsearch_/index.html', output="",
                                   notes="Enter a valid project ID")
        if result:
            output = sort_colnames_ES(output)
            if current_app.config['HOST_PLOT']:
                host = current_app.config['HOST_PLOT']
            return render_template('elasticsearch_/index.html', output=output,
                                   host=host, notes="")
        else:
            msg = 'That project id does not exist'
            print(msg)
            flash(msg, 'warning')
            return render_template('elasticsearch_/index.html', output="")


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
            "task_status": task.get_status(),
            "task_result": f"{task.result}"
        },
        }
    else:
        res_dict = {'status': f"Error! - task_id: {task_id}"}
    return jsonify(res_dict), 202


@ elasticsearch_bp.route("/es/add-task/<hostname>")
def add_task(hostname):
    tsl_file_path = get_filepath_mgdb(hostname)
    print(f'current tsl file: {tsl_file_path}')
    # from xml/mongodb data
    current_row_data = get_latest_rowdata_mgdb(hostname)
    try:
        current_ts = datetime.strptime(
            current_row_data['time'], "%m/%d/%Y %I:%M:%S %p")
    except ValueError as e:
        current_ts = datetime.strptime(
            current_row_data['time'], "%Y-%b-%d %H:%M:%S")

    # pass sample_name as well to assert
    data = prepare_row_data_ES(tsl_file_path, current_row_data['sample_well'],
                               current_row_data['plate_loc'],
                               current_ts,
                               current_app.config['UVDATA_FILE_DIR'], hostname)

    # Send a job to the task queue
    # result_ttl - specifies how long (in seconds) successful jobs and their results are kept
    index_name = current_app.config['ES_INDEX_NAME']
    sleep_time = current_app.config['SLEEP_TIME']
    host = current_app.config['HOSTNAME']
    redis_url = current_app.config['REDIS_URL'].strip().replace('"', '')
    print(f'redis url from add-task endpoint: {redis_url}')

    check, cnt = query_ES_dup_projid(host,
                                     index_name, data['project_id'], data['sample_name'])
    print(f'check duplicate project id: {check}')
    print(f'count for duplicates: {cnt}')
    if check:
        data['project_id'] = data['project_id'] + f"_{cnt}"
    with Connection(redis.from_url(redis_url)):
        q = Queue()
        task = q.enqueue(upload_data_to_ES, args=(host,
                                                  index_name,
                                                  sleep_time,
                                                  data), job_timeout=150, result_ttl=1000)
    q_len = len(q)  # Get the queue length
    enq_time = task.enqueued_at.strftime('%a, %d-%b-%Y %H:%M: %S')
    message = f"""Task {task.id} queued at {enq_time}; len: {q_len} jobs queued"""
    return jsonify({'output': message}), 202
