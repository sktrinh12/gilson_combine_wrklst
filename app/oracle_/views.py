from flask import Blueprint, render_template, request, flash, jsonify
from oracle_.oracle_ import *

oracle_bp = Blueprint(
    'oracle_bp', __name__, template_folder='tempaltes', static_folder='static')


@oracle_bp.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@oracle_bp.route('/oracle')
@oracle_bp.route('/oracle/index.html')
def main():
    with cx_Oracle.connect(ORACLE_USER, ORACLE_PASS, dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(
            f"SELECT * FROM {tableName} WHERE rownum < 11 ORDER BY seq_num, finish_date ASC")
        output = cursor.fetchall()
    return render_template('oracle_/index.html', output=output, notes="**10 most recent runs")


@oracle_bp.route('/oracle/upload_worklist/')
def upload_worklist():
    wl_path = output_file_path()
    print(wl_path)
    with open(wl_path, 'r') as f:
        file_path, hostname = f.readline().strip(',')
        file_dict = {"file_path": file_path, "hostname": hostname}
    return jsonify(file_dict)


@oracle_bp.route('/oracle/filter_proj_id', methods=["GET", "POST"])
def filter_proj_id():
    if request.method == "POST":
        input_proj_id = request.form['filter']
        if check_in_project_ids(input_proj_id):
            with cx_Oracle.connect(ORACLE_USER, ORACLE_PASS, dsn_tns) as con:
                cursor = con.cursor()
                cursor.execute(
                    f"SELECT * FROM {tableName} WHERE PROJECT_ID = '{input_proj_id}' ORDER BY seq_num, finish_date")
                output = cursor.fetchall()
            return render_template('index.html', output=output, notes="")
        else:
            msg = 'That project id does not exist'
            print(msg)
            flash(msg, 'warning')
            return render_template('index.html', output="")
    return render_template('oracle_/index.html', output="", notes="")
