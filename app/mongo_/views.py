from flask import (Blueprint, render_template, request, redirect, flash, jsonify,
                   current_app)
from mongo_.mongo_ import *

mongo_bp = Blueprint('mongo_bp', __name__,
                     template_folder='templates', static_folder='static')


@mongo_bp.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@mongo_bp.route('/mongo/')
@mongo_bp.route('/mongo/index.html')
def main():
    output = list(query_mgdb_latest(current_app.config['MGDB_DBNAME']))
    return render_template('mongo_/index.html', output=output, notes="")


@mongo_bp.route('/mongo/filter_proj_id', methods=["GET", "POST"])
def filter_proj_id():
    if request.method == "POST":
        input_proj_id = request.form['filter']
        result, output = filter_mgdb_data_proj_id(
            current_app.config['MGDB_DBNAME'], input_proj_id)
        if result:
            return render_template('mongo_/index.html', output=output, notes="")
        else:
            msg = f'That project id ({input_proj_id}) does not exist in the database'
            print(msg)
            flash(msg, 'warning')
            return render_template('mongo_/index.html', output="")
    return render_template('mongo_/index.html', output="", notes="")


@mongo_bp.route('/mongo/uvplot/<project_id>/<sample_well>')
def uvplot(project_id, sample_well):
    data_dict = get_mongo_data(
        current_app.config['MGDB_DBNAME'], project_id, sample_well)
    plot = create_plot(data_dict)
    return render_template('plot.html', plot=plot, data_dict=data_dict)


@mongo_bp.route('/mongo/job-results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    job = Job.fetch(job_id, connection=conn)

    if job.is_finished:
        res_dict = {'output': f"Job Finished: {job.result}"}
        return jsonify(res_dict), 200
    else:
        res_dict = {'output': f"Job not finished! - id: {job_id}"}
        return jsonify(res_dict), 202


@mongo_bp.route("/mongo/add-task")
def add_task():
    jobs = app.q.jobs  # Get a list of jobs in the queue
    xml_file = get_newest_xmlfile(current_app.config['XML_PARENT_DIR'])
    wl_path = output_file_path()
    with open(wl_path, 'r') as f:
        content = f.readline().split(',')
    tsl_file_path = content[0].strip()
    hostname = content[1].strip()
    print(tsl_file_path)
    print(hostname)
    message = None
    data = format_row_data_to_dict(prepare_row_data(tsl_file_path, xml_file,
                                                    current_app.config['UVDATA_FILE_DIR'], hostname))
    if data:
        # Send a job to the task queue
        sleep_time = app.config['SLEEP_TIME']
        db_name = app.config['MGDB_DBNAME']

        with Connection(redis.from_url(os.getenv('REDIS_URL'))):
            q = Queue()
            task = q.enqueue(upload_mongodb, args=(db_name,
                                                   sleep_time, data),
                             job_timeout=150, result_ttl=1000)
        # task = app.q.enqueue(upload_mongodb, args=('gilson_logs',
        #                                            10, data), job_timeout=15, result_ttl=1000)
        jobs = q.jobs  # Get a list of jobs in the queue
        q_len = len(q)  # Get the queue length
        message = f"Task {task.id} queued at {task.enqueued_at.strftime('%a, %d %b %Y %H:%M:%S')}. {q_len} jobs queued"

    return f"message={message}, jobs={jobs}"
