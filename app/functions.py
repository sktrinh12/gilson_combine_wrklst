import pandas as pd
import numpy as np
import os
from functions import *
from flask import current_app as app
import re
import time
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from plotly.utils import PlotlyJSONEncoder
import plotly.graph_objs as go
import json
import ntpath
from flask import current_app as app

# static variables
REGEX_TIMESTAMP = r'(20)\d\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])_\d{2}-\d{2}-\d{2}-[PA]M'


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


# def bkg_task():
#     for i in range(7, 0, -1):
#         print(f'{i} secs left')
#         time.sleep(1)
#     print()
#     print('finished')


# def prepare_row_data(tsl_file_path, xml_log_file, uvdata_file_dir, hostname):
#     '''print out the current running row data from raw worklist file and then
#     repare for sql entry; this is an older version that uses txt files; NOT
#     ORACLE TABLES
#     Returns a list not a dictionary'''

#     tsl_file_name = path_leaf(tsl_file_path)
#     projectid = tsl_file_name.split('_', 1)[0]

#     # parse XML file
#     xml_data_row_dict, row_count = get_xml_text(
#         ntpath.join(app.config['XML_PARENT_DIR'], xml_log_file))

#     # get sample well location
#     sw_loc = get_sample_well_loc(xml_data_row_dict, row_count)

#     # get current row data
#     current_row_list = read_tsl_file(tsl_file_path, sw_loc)
#     current_row_dict = convert_to_dict(current_row_list)

#     # convert AM/PM time to 24-hr format and with month name
#     current_time = datetime.strptime(
#         xml_data_row_dict[f'{row_count}_time'], orig_date_fmt).strftime('%Y-%b-%d %H:%M:%S')

#     # get current uvdata csv file
#     uvdata_file = get_current_uvdata_file(
#         uvdata_file_dir, current_row_dict['sample_name'])

#     assert current_row_dict['sample_well'] == xml_data_row_dict[f'{row_count}_sample_well'], \
#         'sample well mis-match "{0}" does not equal "{1}"'.format(
#             current_row_dict['sample_well'], xml_data_row_dict[f'{row_count}_sample_well'])

#     # assert current_row_dict['notes'] == xml_data_row_dict[f'{row_count}_notes'], \
#     #    'notes mis-match "{0}" does not equal "{1}"'.format(current_row_dict['notes'], xml_data_row_dict[f'{row_count}_notes'])

#     assert current_row_dict['plate_loc'] == xml_data_row_dict[f'{row_count}_plate_loc'], \
#         'plate location mis-match "{0}" does not equal "{1}"'.format(
#             current_row_dict['plate_loc'], xml_data_row_dict[f'{row_count}_plate_loc'])

#     df = pd.read_csv(os.path.join(uvdata_file_dir, uvdata_file))
#     field_names = get_field_names(df)
#     channel_names = get_chnl_names(df)
#     data_dict = gen_data_dict(
#         channel_names, sep_data_into_lists(df, channel_names))

#     # with con.cursor() as cursor:
#     row_data = [current_time,
#                 projectid,
#                 hostname,
#                 current_row_dict['method_name'],
#                 current_row_dict['sample_name'],
#                 current_row_dict['barcode'],
#                 current_row_dict['brooks_bc'],
#                 current_row_dict['id_suffix'],
#                 sw_loc,
#                 current_row_dict['plate_loc'],
#                 tsl_file_name,
#                 path_leaf(xml_log_file),
#                 path_leaf(uvdata_file),
#                 data_dict
#                 ]
#     return row_data


def create_plot(dict_data):
    df = pd.DataFrame(dict_data['uvdata'])
    df = change_dtype(df)
    df = shift_baseline(df)
    xs = np.linspace(0, 12.62, df.shape[0])
    data = list()

    for cn in df.columns:
        if re.search(r'\d', cn):
            name = f'{cn} nm'
        else:
            name = cn
        data.append(go.Scatter(x=xs, y=df[cn],
                               mode='lines',
                               name=name,
                               hoverinfo='skip')
                    )
    # solvent gradient
    xs, ys = gen_solv_data(df, xs)

    data.append(
        go.Scatter(x=xs, y=ys,
                   mode='lines',
                   line=dict(color='grey', width=2),
                   name='solv grad', yaxis="y2",
                   hoverinfo='skip')
    )

    # Add Line Vertical
    annotations = list()
    shapes = list()
    for idx, i in enumerate(np.arange(1.5, 12.5, 0.5)):
        data.append(  # add invisible filled trace for hovering
            go.Scatter(
                x=[i, i, i+0.49, i+0.49, i],
                y=[0, 2, 2, 0, 0],
                fill="toself",
                fillcolor='grey',
                showlegend=False,
                hoverinfo='skip',
                # hovertemplate=f"{dict_data['plate_loc']}:FX_{idx+1}",
                mode='text',
                # name=f"{dict_data['plate_loc']}:FX_{idx+1}",
                opacity=0.1
            )
        )
        shapes.append(
            dict(
                type="line",
                x0=i,
                y0=0,
                x1=i,
                y1=2,
                xref='x',
                yref='y',
                name='',
                line=dict(
                    color="grey",
                    width=0.5,
                    dash='dot'
                )
            )
        )

        annotations.append(
            dict(
                x=i+0.25,
                y=1.9,
                xref="x",
                yref="y",
                text=f"{idx+1}",
                font=dict(
                    family="Courier New, monospace",
                    size=13,
                    color="#ffffff"
                ),
                align="center",
                showarrow=False,
                bordercolor="#c7c7c7",
                borderwidth=1,
                borderpad=2,
                bgcolor="#2b3f75",
                # bgcolor="#ff7f0e",
                opacity=0.8
            )
        )

    layout = go.Layout(
        shapes=shapes,
        font_family="Courier New, monospace",
        hovermode="closest",
        margin={
            'l': 35,
            'r': 35,
            'b': 35,
            't': 35,
            'pad': 2
        },
        xaxis=dict(
            title="Minutes",
            domain=[0.12, 1],
            showspikes=True
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
            range=[0, 101]
        ),
        # hoverlabel=dict(
        #     bgcolor="#2b3f75",
        #     font_size=17,
        #     font_family="Rockwell",
        # ),
        annotations=annotations
    )

    fig = dict(data=data, layout=layout)
    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)
    return graphJSON


def output_file_path():
    wl_file = f'{app.root_path}/WORKLIST_FILEPATH.txt'
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


def grab_rows(fi_content_df):
    '''Grab the valid rows from the tsl worklist file'''
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


def extract_datetime(datetime_string):
    return datetime.strptime(re.search(REGEX_TIMESTAMP,
                                       datetime_string).group(0),
                             '%Y-%m-%d_%I-%M-%S-%p')


def compare_timestamp(file_name_path, xml_ts, within_time=timedelta(minutes=7)):
    # compare the timestampe of the uvdata file name with xml file time stamp
    # the xml file is ahead by 5ish minutes bc set in method to log the data at
    # 5ish minutes, so will be higher than the uvdata time stamp
    uvdata_ts = extract_datetime(file_name_path)
    td = xml_ts - uvdata_ts
    print(f"xml ts: {xml_ts} - uv ts: {uvdata_ts}")
    if td > within_time:
        return False, td
    else:
        return True, td


def get_current_uvdata_file(uvdata_file_directory, sample_name, xml_ts):
    '''
         find csv file that is within the current timestampe (today) and matches the sample name
    '''
    files = [fi for fi in os.listdir(uvdata_file_directory)]
    uvdata_file_filters = [lambda x:
                           os.path.isfile(os.path.join(uvdata_file_directory, x)), lambda x: x.endswith('.csv'), lambda x: re.search(f'{sample_name}', x)]
    files = list(filter(lambda x: all(
        [f(x) for f in uvdata_file_filters]), files))
    assert files, f"Did not find {sample_name} uv data .csv file in directory:{uvdata_file_directory}"

    check_file_ts = compare_timestamp(
        os.path.join(uvdata_file_directory, files[0]), xml_ts)
    print(f'check file ts: {check_file_ts[0]}; {check_file_ts[1]}')
    # assert check_file_ts[0] == True, \
    #     'raw uv-data file is older by {0} than the allowed timeframe; is it the correct file? - sample name:"{1}" questionable file: "{2}"'.format(
    #     str(check_file_ts[1]), sample_name, files[0])
    return files[0]


def get_newest_xmlfile(xml_file_directory):
    '''
        return newest file for reading/parsing
    '''
    files = [fi for fi in os.listdir(xml_file_directory)]
    xml_filters = [lambda x: os.path.isfile(
        os.path.join(xml_file_directory, x)), lambda x: x.endswith('.xml')]
    files = list(filter(lambda x: all(
        [f(x) for f in xml_filters]), files))
    files = [os.path.join(xml_file_directory, f)
             for f in files]  # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    assert files, f"No XML file found with given search constraints in {xml_file_directory}"
    return files[0]


def get_rows_xml(root):
    # number of rows of data - 1 for the header
    return len([r for r in root[1][0]]) - 1


def get_xml_text(xmlfile):
    tree = ET.parse(xmlfile)
    root = tree.getroot()
    cnt_rows = get_rows_xml(root)
    data_row_dict = dict()
    row_line = 0
    for row in root[1][0]:
        data_cnt = 0
        for cell in row:
            if cell.items()[0][1] == "NormalStyle":
                for data in cell:
                    if data_cnt == 0:
                        data_row_dict[f'{row_line}_time'] = data.text
                    if data_cnt == 4:
                        data_row_dict[f'{row_line}_notes'] = data.text
                    if data_cnt == 6:
                        data_row_dict[f'{row_line}_sample_well'] = data.text
                    if data_cnt == 7:
                        data_row_dict[f'{row_line}_plate_loc'] = data.text
                data_cnt += 1
        row_line += 1

    return data_row_dict, cnt_rows


def get_sample_well_loc(data_row_dict, cnt_rows):
    return data_row_dict[f'{cnt_rows}_sample_well']


def read_tsl_file(file_path, sample_well_loc):
    count = 0
    with open(file_path, 'r') as f:
        while True:
            count += 1
            line = f.readline()
            current_row_data = get_current_run_row(line, sample_well_loc)
            if current_row_data:
                break

            if not line:
                break
    if not current_row_data:
        raise AttributeError(
            f"Current sample well not found in TSL file: {sample_well_loc}")
    return current_row_data


def get_current_run_row(tsl_row, sample_well_loc):
    try:
        if re.search(fr'\t(?![0]){sample_well_loc}\t', tsl_row):
            print()
            print(f'current tsl row: {tsl_row}')
            return tsl_row.split('\t')[1:]
    except AttributeError:
        print('None found')
        return None


def convert_to_dict(current_row_list):
    '''convert tab separated line from tsl file into a dictionary'''
    current_row_dict = {}
    brooks_bc, id_suffix = current_row_list[current_row_list.index(
        '...') + 1].split('/')
    current_row_dict['method_name'] = current_row_list[0].strip()
    current_row_dict['sample_name'] = current_row_list[1].strip()
    current_row_dict['barcode'] = current_row_list[3].strip()
    current_row_dict['brooks_bc'] = brooks_bc.strip()
    current_row_dict['id_suffix'] = id_suffix.strip()
    current_row_dict['plate_loc'] = current_row_list[-1].strip()
    #current_row_dict['notes'] = current_row_list[4]
    current_row_dict['sample_well'] = current_row_list[-2]
    return current_row_dict


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


def sep_data_into_lists(df, channel_names):
    data_dict = {ch_name: [] for ch_name in channel_names}

    for i, r in df.iloc[26:].iterrows():
        tmp_ = r[' Step Info'].split('\t')
        if i % 10 == 0:  # reduce sample rate
            data_dict[channel_names[0]].append(tmp_[0])
            data_dict[channel_names[1]].append(tmp_[1])
            data_dict[channel_names[2]].append(tmp_[2])
            data_dict[channel_names[3]].append(tmp_[3])

    return [val for val in data_dict.values()]


def gen_data_dict(channel_names, channel_vals):
    return {ch_nm: ch_vals for ch_nm, ch_vals in zip(channel_names, channel_vals)}


def gen_solv_data(df, xs):
    '''generates solvent gradient data for plotting'''
    # the index in the np.array, `xs` that corresponds to 1.5min, 9min, 12.5min
    idx_15, idx_9, idx_125 = (
        np.where((xs < j+0.01) & (xs > j-0.01))[0][0] for j in [1.5, 9, 12.5])
    # mean difference between points in the np.array
    steps = np.mean(np.diff(xs))
    # 12.62+0.01 so that the downward slope doesnt have a kink on it
    last_phase = np.arange(12.63, 15, steps)
    # add the last phase (plateau) of the gradient curve based on a np.arange(0,12.62)
    idx_13 = np.where((last_phase > 12.99) & (last_phase < 13.02))[0][0]
    xs_ext = np.concatenate((xs, last_phase))
    solv_grad_data = np.concatenate((np.repeat(30, idx_15),
                                     np.linspace(30, 100, idx_9-idx_15),
                                     np.repeat(100, idx_125-idx_9),
                                     np.linspace(100, 30, idx_13),
                                     np.repeat(30, len(last_phase) - idx_13)
                                     ))
    return xs_ext, solv_grad_data


def shift_baseline(df):
    d_min = df.min().min()
    # correct baseline to be at zero by add to all values the min value
    for cn in df.columns:
        df[cn] = df[cn].apply(lambda x: x + abs(d_min))
    return df


def change_dtype(df):
    for ch in df.columns:
        df[ch] = df[ch].astype('float')
    return df


def format_row_data_to_dict(row_data):
    '''format the row of data including uv data into a dictionary'''
    key_names = [
        'time_stamp',
        'project_id',
        'gilson_number',
        'method_name',
        'sample_name',
        'barcode',
        'brooks_barcode',
        'id_suffix',
        'sample_well',
        'plate_loc',
        'tsl_file_name',
        'xml_file_name',
        'uvdata_file_name',
        'uvdata'
    ]
    return {k: v for k, v in zip(key_names, row_data)}
