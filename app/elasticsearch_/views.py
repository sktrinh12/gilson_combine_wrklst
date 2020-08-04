from flask import (Blueprint, render_template, request,
                   flash, jsonify, current_app)
from elasticsearch_.elasticsearch_ import *
from oracle_.oracle_ import query_ordb_curr_row, get_tsl_filepath_ordb


elasticsearch_bp = Blueprint(
    'elasticsearch_bp', __name__, template_folder='templates', static_folder='static')


@elasticsearch_bp.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@elasticsearch_bp.route('/')
@elasticsearch_bp.route('/es/index.html')
def main():
    output = query_ES_latest(current_app.config['ES_INDEX_NAME'], 8)
    output = sort_colnames_ES(output)
    print(output)

    return render_template('elasticsearch_/index.html', output=output, notes="")


@elasticsearch_bp.route('/es/show-jsondata/')
def show_jsondata():
    '''shows the output as a json format; the `prepare_row_data` is a former
    function that returns a list, thus `format_row_data_to_dict` will convert it
    to a diciontary for the view'''
    xml_file = get_newest_xmlfile('/Users/trinhsk/Documents')
    wl_path = output_file_path()
    with open(wl_path, 'r') as f:
        content = f.readline().split(',')
    tsl_file_path = content[0].strip()
    hostname = content[1].strip()
    print(tsl_file_path)
    print(hostname)
    return format_row_data_to_dict(prepare_row_data(tsl_file_path, xml_file,
                                                    uvdata_file_dir, hostname))


@elasticsearch_bp.route('/es/uvplot/<project_id>/<sample_well>')
def uvplot(project_id, sample_well):
    data_dict = query_ES_data(
        current_app.config['ES_INDEX_NAME'], project_id, sample_well)
    plot = create_plot(data_dict)
    return render_template('elasticsearch_/plot.html', plot=plot, data_dict=data_dict)


@elasticsearch_bp.route('/es/filter_proj_id', methods=["GET", "POST"])
def filter_proj_id():
    if request.method == "POST":
        input_proj_id = request.form['filter']
        result, output = check_ES_proj_id(
            current_app.config['ES_INDEX_NAME'], input_proj_id)
        if result:
            output = sort_colnames_ES(output)
            return render_template('elasticsearch_/index.html', output=output, notes="")
        else:
            msg = 'That project id does not exist'
            print(msg)
            flash(msg, 'warning')
            return render_template('elasticsearch_/index.html', output="")
    return render_template('elasticsearch_/index.html', output="", notes="")


@elasticsearch_bp.route('/es/job-results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    job = Job.fetch(job_id, connection=conn)

    if job.is_finished:
        res_dict = {'output': f"Job Finished: {job.result}"}
        return jsonify(res_dict), 200
    else:
        res_dict = {'output': f"Job not finished! - id: {job_id}"}
        return jsonify(res_dict), 202


@elasticsearch_bp.route("/es/add-task/<hostname>")
def add_task(hostname):
    # xml_file = get_newest_xmlfile('/Users/trinhsk/Documents')
    # wl_path = output_file_path()
    # with open(wl_path, 'r') as f:
    #     content = f.readline().split(',')
    # tsl_file_path = content[0].strip()
    # hostname = content[1].strip()
    tsl_file_path = get_tsl_filepath_ordb(hostname)
    print(f'current tsl file: {tsl_file_path}')
    print(f'hostname: {hostname}')
    message = None
    current_row_data = [x for i, x in enumerate(
        query_ordb_curr_row(hostname))]
    current_ts = current_row_data[0]
    # current_notes = current_row_data[1]
    current_sample_well = current_row_data[2]
    current_plate_loc = current_row_data[3]
    # data = prepare_row_data_ES(tsl_file_path, xml_file,
    #                            uvdata_file_dir, hostname)
    data = prepare_row_data_ES(tsl_file_path, current_sample_well,
                               current_plate_loc, current_ts,
                               current_app.config['UVDATA_FILE_DIR'], hostname)
    # upload_data_to_ES(data)
    # return jsonify({'output': 'upload successful'}), 200
    # task = q.enqueue(bkg_task, job_timeout=15, result_ttl=1000)

    # Send a job to the task queue
    # result_ttl - specifies how long (in seconds) successful jobs and their results are kept
    index_name = current_app.config['ES_INDEX_NAME']
    sleep_time = current_app.config['SLEEP_TIME']

    check, cnt = query_ES_dup_projid(
        index_name, data['project_id'], data['sample_name'])
    print(f'check duplicate project id: {check}')
    print(f'count for duplicates: {cnt}')
    if check:
        data['project_id'] = data['project_id'] + f"_{cnt}"

    task = current_app.q.enqueue(upload_data_to_ES, args=(index_name,
                                                          sleep_time,
                                                          data), job_timeout=15, result_ttl=1000)
    q_len = len(current_app.q)  # Get the queue length
    enq_time = task.enqueued_at.strftime('%a, %d-%b-%Y %H:%M: %S')
    message = f"""Task {task.id} queued at {enq_time}; len: {q_len} jobs queued"""
    return jsonify({'output': message})
