from functions import *
from init import *

tableName = 'GILSON_RUN_LOGS'


@app.route('/')
@app.route('/index.html')
def main():
    with cx_Oracle.connect(ORACLE_USER, ORACLE_PASS, dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(
            f"SELECT * FROM {tableName} WHERE rownum < 11 ORDER BY seq_num, finish_date ASC")
        output = cursor.fetchall()
    return render_template('index.html', output=output, notes="**10 most recent runs")


@app.route('/filter_proj_id', methods=["GET", "POST"])
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
    return render_template('index.html', output="", notes="")


@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@app.route('/upload_worklist/')
def upload_worklist():
    wl_path = output_file_path()
    with open(wl_path, 'r') as f:
        file_path_dict = {"file_path": f.readline().strip()}
    return jsonify(file_path_dict)


@app.route('/dataframe/')
def display_dataframe():
    # get the worklist path from the text file (hta regedit)
    wl_path = output_file_path()
    with open(wl_path, 'r') as f:
        file_path = f.readline().strip()
    if 'mnt' in wl_path:
        file_name = file_path.split('/')[-1]
        file_path = os.path.join('/mnt/tsl_dir', file_name)
    df = imbue_rows(file_path)
    return render_template('dataframe.html',  tables=[df.to_html(classes='data', index=False, header="true")], tsl_file_name=file_path)


@app.route('/uvplot/')
def uvplot():
    export_file = '/Users/trinhsk/Downloads/sample_export_file.csv'
    df = pd.read_csv(export_file)
    field_names = get_field_names(df)
    channel_names = get_chnl_names(df)
    ch1, ch2, ch3, ch4 = sep_data_into_lists(df)
    data_dict = gen_data_dict(channel_names, [ch1, ch2, ch3, ch4])
    df = pd.DataFrame(data=data_dict)
    for ch in channel_names:
        df[ch] = df[ch].astype('float')
    plot = create_plot(df, field_names)
    return render_template('plot.html', plot=plot)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8003, debug=True)
