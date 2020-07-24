import cx_Oracle
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime
from socket import gethostname
from plotly.utils import PlotlyJSONEncoder
import plotly.graph_objs as go
import json

ORACLE_HOST = os.environ['ORACLE_HOST']
ORACLE_PORT = os.environ['ORACLE_PORT']
ORACLE_SERVNAME = os.environ['ORACLE_SERVNAME']
ORACLE_PASS = os.environ['ORACLE_PASS']
ORACLE_USER = os.environ['ORACLE_USER']

dsn_tns = cx_Oracle.makedsn(
    ORACLE_HOST, ORACLE_PORT, service_name=ORACLE_SERVNAME)
column_headers = ['SEQ_NUM', 'FINISH_DATE', 'PROJECT_ID', 'METHOD_NAME', 'SAMPLE_NAME',
                  'BARCODE', 'PLATE_ID', 'BROOKS_BARCODE', 'SAMPLE_WELL', 'PLATE_POSITION', 'GILSON_NUMBER']


def get_field_names(df):
    field_names = ['iteration', 'sample_well', 'sample_name',
                   'barcode', 'run_name', 'run_date', 'method_start_time']
    field_idices = [1, 2, 3, 4, 10, 11, 12]
    field_dict = {}
    for i, fn in zip(field_idices, field_names):
        field_dict[fn] = df.iloc[i].values[0].split(':', 1)[1]
    return field_dict


def get_chnl_names(df):
    return [ch.split(':')[1] for ch in df.iloc[19].values[0].split('\t')]


def sep_data_into_lists(df):
    ch_1 = []
    ch_2 = []
    ch_3 = []
    ch_4 = []

    for i, r in df.iloc[26:].iterrows():
        tmp_ = r[' Step Info'].split('\t')
        if i % 10 == 0:  # reduce sample rate
            ch_1.append(tmp_[0])
            ch_2.append(tmp_[1])
            ch_3.append(tmp_[2])
            ch_4.append(tmp_[3])
    return ch_1, ch_2, ch_3, ch_4


def gen_data_dict(channel_names, channel_list):
    return {ch_nm: ch_nbr for ch_nm, ch_nbr in zip(channel_names, channel_list)}


def gen_solv_data(df, xs):
    idx_15, idx_9, idx_125 = (
        np.where((xs < j+0.01) & (xs > j-0.01))[0][0] for j in [1.5, 9, 12.5])
    steps = np.mean(np.diff(xs))
    last_phase = np.arange(12.62, 15, steps)
    idx_13 = np.where((last_phase > 12.99) & (last_phase < 13.02))[0][0]
    xs_ext = np.concatenate((xs, last_phase))
    solv_grad_data = np.concatenate((np.repeat(30, idx_15),
                                     np.linspace(30, 100, idx_9-idx_15),
                                     np.repeat(100, idx_125-idx_9),
                                     np.linspace(100, 30, idx_13),
                                     np.repeat(30, len(last_phase) - idx_13)
                                     ))
    return xs_ext, solv_grad_data


def shift_baseline(df, channel_names):
    d_min = df.min().min()
    # correct baseline to be at zero by add to all values the min value
    for cn in channel_names:
        df[cn] = df[cn].apply(lambda x: x + abs(d_min))
    return df


def create_plot(df, field_dict):
    xs = np.linspace(0, 12.62, df.shape[0])
    data = []
    for cn in df.columns:
        if re.search(r'\d', cn):
            name = f'{cn} nm'
        else:
            name = cn
        data.append(go.Scatter(x=xs, y=df[cn],
                               mode='lines',
                               name=name)
                    )
    # solvent gradient
    xs, ys = gen_solv_data(df, xs)
    data.append(
        go.Scatter(x=xs, y=ys,
                   mode='lines',
                   name='solv grad', yaxis="y2")
    )

    layout = go.Layout(
        title="UV and Solvent gradient trace of {0}\nBarcode: {1}".format(
            field_dict['sample_name'], field_dict['barcode']),
        xaxis=dict(
            title="Minutes",
            domain=[0.12, 1]
        ),
        yaxis=dict(
            title="UV Abs",
            range=[-0.1, 2.1],
            position=0.1,
            showgrid=False
        ),
        yaxis2=dict(
            title="Solvent Gradient  (%)",
            anchor="free",
            domain=[0.1, 1],
            overlaying="y",
            side="left",
            position=0,
            range=[0, 102])
    )
    fig = dict(data=data, layout=layout)
    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)
    return graphJSON


def dply_cfg():
    return {
        'displayModeBar': True,
        'editable': True,
        'showLink': False,
        'displaylogo': False
    }


def output_file_path():
    wl_file = 'WORKLIST_FILEPATH.txt'
    mnt_dr = '/mnt/worklist_dir'
    wl_path = os.path.join(mnt_dr, wl_file)
    if not os.path.exists(wl_path):
        return wl_file
    else:
        return wl_path


def convert_to_file_path(input_file_path):
    if '/' not in input_file_path and '-' in input_file_path:
        file_path = '/'
        for _ in input_file_path.split('-'):
            file_path += _ + '/'
        return file_path[:-1]
    else:
        return input_file_path


def check_in_project_ids(input_project_id):
    '''Gets the distinct project ids to verify the inputted value is valid'''
    with cx_Oracle.connect(ORACLE_USER, ORACLE_PASS, dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(f"SELECT DISTINCT PROJECT_ID FROM GILSON_RUN_LOGS")
        proj_ids = cursor.fetchall()
    proj_ids = [_[0] for _ in proj_ids]
    if input_project_id in proj_ids:
        return True
    else:
        return False


def grab_rows(fi_content_df):
    '''Grab the valid rows from the worklist file'''
    row_idx = []
    for i in range(fi_content_df.shape[0]):
        try:
            if pd.isna(fi_content_df['#Plate_Sample[True,115,13]'][i]):
                pass  # print('nothing')
            else:
                row_idx.append(i)
        except TypeError:
            print(i)
    return row_idx


def split_string_input_file(input_file):
    '''handles if contains filepath separator'''
    if '/' in input_file:
        input_file = input_file.split('/')[-1]
    elif '\\' in input_file:
        input_file = input_file.split('\\')[-1]
    return input_file


def get_column_names_db(cursor):
    cursor.execute(
        "SELECT column_name FROM all_tab_cols WHERE table_name = 'GILSON_RUN_LOGS'")
    output = cursor.fetchall()
    return [_[0] for _ in output]


def imbue_rows(dir_fi, gil_num=gethostname()):
    '''print out each row after extracting data from raw worklist file and then repare for sql entry'''
    # check to see if the file path has '/'
    tmp_dir_fi = split_string_input_file(dir_fi)
    split_fi_name = tmp_dir_fi.split('_')
    projectid = split_fi_name[0]
    # read into pandas df and coerce datatypes to string
    fi_content_df = pd.read_csv(dir_fi, sep='\t', dtype={'NOTES_STRING[False,68,9]': str,
                                                         'SampleId[False,90,5]': str})
    # ensure strings for each value
    fi_content_df['SampleId[False,90,5]'] = fi_content_df['SampleId[False,90,5]'].apply(
        lambda x: 'NaN')
    fi_content_df['SampleAmount[False,78,3]'] = fi_content_df['SampleAmount[False,78,3]'].apply(
        lambda x: f"{str(x)}")
    fi_content_df['#Sample Well[True,109,10]'] = fi_content_df['#Sample Well[True,109,10]'].apply(
        lambda x: f"{str(x)}")
    # split string and create new column
    fi_content_df['plateid'] = fi_content_df['NOTES_STRING[False,68,9]'].apply(
        lambda x: x.split('/')[1].strip() if not pd.isna(x) else '0')
    fi_content_df['brooks_barcode'] = fi_content_df['NOTES_STRING[False,68,9]'].apply(
        lambda x: x.split('/')[0].strip() if not pd.isna(x) else '0')

    # get the valid row indices (non-flush/std/shutdown)
    row_idx = grab_rows(fi_content_df)

    current_time = datetime.now().strftime("%Y-%b-%d %H:%M")

    with cx_Oracle.connect(ORACLE_USER, ORACLE_PASS, dsn_tns) as con:
        tmp_df_list = []
        cursor = con.cursor()
        return_df = pd.DataFrame(columns=column_headers)
        for i in range(24):
            row_data = ["BLANK"]*11
            row_data[0] = i
            row_data[1] = current_time
            row_data[2] = projectid
            row_data[9] = i
            row_data[10] = gil_num
            try:
                rdata_df = fi_content_df.iloc[row_idx[i]]
                row_data[3] = rdata_df['MethodName[True,239,1]']
                row_data[4] = rdata_df['SampleName[True,108,2]']
                row_data[5] = rdata_df['SampleDescription[False,120,4]']
                row_data[6] = rdata_df['plateid']
                row_data[7] = rdata_df['brooks_barcode']
                row_data[8] = str(
                    int(float(rdata_df['#Sample Well[True,109,10]'])))
                row_data[9] = rdata_df['#Plate_Sample[True,115,13]']
            except IndexError:
                pass  # print('passing as a blank ...')
            tmp_df_list.append(row_data)
            # print(row_data)
            #cursor.execute(f"""insert into GILSON_RUN_LOGS values (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)""", row_data)
        # con.commit()
        return return_df.append(pd.DataFrame(tmp_df_list, columns=column_headers))
