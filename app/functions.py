import pandas as pd
import numpy as np
import os
from math import ceil
from functions import *
from flask import current_app as app
import re
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from plotly.utils import PlotlyJSONEncoder
import plotly.graph_objs as go
import json
import ntpath

# static variables
# REGEX_TIMESTAMP = r'(20)\d\d[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])_\d{2}-\d{2}-\d{2}-[PA]M'
REGEX_TIMESTAMP = r'(20\d\d[-](0[1-9]|1[012])[-]\d{2})(.*)(\d{2}-\d{2}-\d{2}-[PA]M)'


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def create_plot(dict_data):
    df = pd.DataFrame(dict_data['UVDATA'])
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


def extract_datetime(datetime_string):
    '''extract the finish time which is at the end of the file name; have to cut
    it up and then concatenate'''
    print(f'UVDATA file datetime string: {datetime_string}')
    try:
        regex_time = re.search(REGEX_TIMESTAMP, datetime_string)
        the_date = regex_time.group(1)
        finish_time = regex_time.group(4)
        return datetime.strptime(f'{the_date}_{finish_time}', '%Y-%m-%d_%I-%M-%S-%p')
    except AttributeError as e:
        print(
            f'problem extracting date format from uvfile string: {datetime_string} - {e}')
        return None

# def extract_datetime(datetime_string):
#     print(f'UVDATA file datetime string: {datetime_string}')
#     try:
#         return datetime.strptime(re.search(REGEX_TIMESTAMP,
#                                            datetime_string).group(0),
#                                  '%Y-%m-%d_%I-%M-%S-%p')
#     except AttributeError as e:
#         print(
#             f'problem extracting date format from uvfile string: {datetime_string} - {e}')
#         return None


def compare_timestamp(file_name_path, xml_ts, within_time=timedelta(minutes=7)):
    # compare the timestampe of the uvdata file name with xml file time stamp
    # the xml file is ahead by 5ish minutes bc set in method to log the data at
    # 5ish minutes, so will be higher than the uvdata time stamp
    uvdata_ts = extract_datetime(file_name_path)
    if uvdata_ts:
        td = xml_ts - uvdata_ts
        print(f"xml ts: {xml_ts} - uv ts: {uvdata_ts}")
        if td > within_time:
            return False, td
        else:
            return True, td
    else:
        return False, None


def get_current_uvdata_file(uvdata_file_directory, sample_name, xml_ts):
    '''
         find csv file that is within the current timestamp and matches the sample name
    '''
    files = [fi for fi in os.listdir(uvdata_file_directory)]
    uvdata_file_filters = [lambda x:
                           os.path.isfile(os.path.join(uvdata_file_directory, x)), lambda x: x.endswith('.csv'), lambda x: re.search(f'{sample_name}', x)]
    files = list(filter(lambda x: all(
        [f(x) for f in uvdata_file_filters]), files))
    assert files, f"Did not find {sample_name} uv data .csv file in directory:{uvdata_file_directory}"

    if len(files) > 1:
        for each_fi in files:
            check_file_ts = compare_timestamp(
                os.path.join(uvdata_file_directory, each_fi), xml_ts)
            if check_file_ts[0]:
                select_file = each_fi
                print(f'check file ts: {check_file_ts[0]}; {check_file_ts[1]}')
                break
    else:
        check_file_ts = compare_timestamp(
            os.path.join(uvdata_file_directory, files[0]), xml_ts)
        print(f'check file ts: {check_file_ts[0]}; {check_file_ts[1]}')
        select_file = files[0]

    assert check_file_ts[0] == True, \
        'raw uv-data file is older by {0} than the allowed timeframe; is it the correct file? - sample name:"{1}" questionable file: "{2}"'.format(
        str(check_file_ts[1]), sample_name, select_file)

    return select_file


def read_tsl_file(file_path, sample_well_loc):
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
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
            f"Current sample well {sample_well_loc} not found in TSL file: {file_path} ")
    return current_row_data


def get_current_run_row(tsl_row, sample_well_loc):
    try:
        if re.search(fr'\t(?![0]){sample_well_loc}\t', tsl_row):
            print(f'current tsl row: {tsl_row}')
            tsl_row = tsl_row.strip()
            return tsl_row.split('\t')[1:]
    except AttributeError:
        print(
            "Couldn't find current run row: tsl_row: {tsl_row}; sample_well_loc: {sample_well_loc}")
        return None


def convert_to_dict(current_row_list):
    '''convert tab separated line from tsl file into a dictionary'''
    print(current_row_list)
    current_row_dict = {}
    try:
        brooks_bc, id_suffix = current_row_list[current_row_list.index(
            '...') + 1].split('/')
    except ValueError as e:
        # if no '/' in the notes
        raise AttributeError(
            f"The Notes column must have a '/' followed by the plate suffix in the tsl file - error msg: {e}")
    current_row_dict['METHOD_NAME'] = current_row_list[0].strip()
    current_row_dict['SAMPLE_NAME'] = current_row_list[1].strip()
    current_row_dict['BARCODE'] = current_row_list[3].strip()
    current_row_dict['BROOKS_BARCODE'] = brooks_bc.strip()
    current_row_dict['PLATE_ID'] = id_suffix.strip()
    current_row_dict['PLATE_POSITION'] = current_row_list[-1].strip()
    current_row_dict['SAMPLE_WELL'] = current_row_list[-2]
    return current_row_dict


# def get_field_names(df):
#     '''get column/field names of uv data file; set fixed field names for easy
#     reading/accessing in othe rfunctions'''
#     field_names = ['iteration', 'sample_well', 'sample_name',
#                    'barcode', 'run_name', 'run_date', 'method_start_time']
#     field_idices = [1, 2, 3, 4, 10, 11, 12]
#     field_dict = {}
#     for i, fn in zip(field_idices, field_names):
#         field_dict[fn] = df.iloc[i].values[0].split(':', 1)[1]
#     return field_dict


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


def srchmap_tslfile_dictdf(list_of_rack_nbrs, tslfile_dir):
    '''search a given directory for tsl files that match rack number and store
    pd df into dictionary'''
    dct_df = {}
    for rk in list_of_rack_nbrs:
        for fi in os.listdir(tslfile_dir):
            if re.search(fr'^{rk}', fi):
                dct_df[rk] = pd.read_csv(
                    os.path.join(tslfile_dir, fi), sep='\t')
                if rk == list_of_rack_nbrs[0]:
                    continue
                else:
                    break
    return dct_df


def find_end_idx_sw(df):
    '''find the end index row and sample well number for the first rack'''
    for i in range(df.shape[0]-1, 0, -1):
        sw_value = df.loc[i, '#Sample Well[True,109,10]']
        if sw_value != 0:
            return i, sw_value


def incr_plt_loc(plate_loc, incr):
    '''increment the plate location number for combining the worklists'''
    suffix_nbr = plate_loc[-3:]
    curr_val = int(re.search(r'\d{2}S', plate_loc).group(0)[:2]) + incr
    if curr_val < 10:
        curr_val = f'0{curr_val}'
    return f'P{curr_val}{suffix_nbr}'


def get_end_plt_idx(df, end_idx):
    '''get the last (ending) plate location index'''
    plate_loc = df.loc[end_idx, '#Plate_Sample[True,115,13]']
    return int(re.search(r'\d{2}S', plate_loc).group(0)[:2])


def base_combine_worklists(df1, df2):
    '''combine two worklists using pandas'''
    sw_buffer = 0
    # remove rows that don't have sample well number
    df1 = df1[~df1['#Plate_Sample[True,115,13]'].isna()]
    df2 = df2[~df2['#Plate_Sample[True,115,13]'].isna()]
    df1.reset_index(inplace=True, drop=True)
    df2.reset_index(inplace=True, drop=True)

    row_cnt = df1.shape[0]
    if row_cnt % 4 != 0:
        # add to the incr counters to make sample wells in the next iteration
        sw_buffer = 4 - (row_cnt % 4)

    # new sample well starting number for second rack (df2)
    end_idx, start_sw = find_end_idx_sw(df1)
    print(end_idx)
    start_sw += sw_buffer
    incr = get_end_plt_idx(df1, end_idx)
    print(f'incr: {incr}')
    print(f'sw_buffer: {sw_buffer}')
    # re-assign sample well as a increment of last sample well value from first rack (df1)
    df2.loc[:, '#Sample Well[True,109,10]'] = df2['#Sample Well[True,109,10]'].map(
        lambda x: x + start_sw)
    df2.loc[:, '#Plate_Sample[True,115,13]'] = df2['#Plate_Sample[True,115,13]'].map(
        lambda x: incr_plt_loc(x, incr))
    df = pd.concat([df1, df2])
    # print(df.shape)

    colour_css_cls = ['tbl-colour-grp-1',
                      'tbl-colour-grp-2']  # ['#f8f3eb', '#e0dede']
    # make conditions for assigning colours; first get unique plate location prefixes i.e. 'P01'
    unq_prefx_plt = df['#Plate_Sample[True,115,13]'].apply(
        lambda x: x[:3]).unique()
    # second, use a regex contains string to compare and get list of list of booleans that show matches
    conditions = [df['#Plate_Sample[True,115,13]'].str.contains(
        pl_prx) for pl_prx in unq_prefx_plt]
    # colour assignment hex-colour (2 options) that will be selected based on the position of the condition
    choices = colour_css_cls*int(unq_prefx_plt.shape[0]/2)
    # np.tile(np.repeat(colour, 4), int(df.shape[0]/4/2))
    df['colour_css_cls'] = np.select(conditions, choices, default=np.nan)

    return df


def insert_row_(row_number, df, row_value):
    df_result = pd.DataFrame()
    if isinstance(row_number, list):
        for rn in row_number:
            if not df_result.empty:
                df = df_result
            df1 = df[0:rn]
            df2 = df[rn:]
            if row_value.shape[0] > 1:
                for i in range(row_value.shape[0]):
                    df1.loc[rn+i] = row_value[i]
            else:
                df1.loc[rn] = row_value
            df_result = pd.concat([df1, df2])
            df_result.index = [*range(df_result.shape[0])]
    else:
        # if just one row number to insert at
        df1 = df[0:row_number]
        df2 = df[row_number:]
        if row_value.shape[0] > 1:
            # if multiple rows to insert
            for i in range(row_value.shape[0]):
                df1.loc[row_number+i] = row_value[i]
        else:
            df1.loc[row_number] = row_value
        df_result = pd.concat([df1, df2])
        df_result.index = [*range(df_result.shape[0])]

    return df_result


def main_combine_worklists(df1, df2):
    startup_rows = df1.iloc[:3]
    startup_rows['colour'] = np.nan
    shutdown_rows = df1.iloc[-3:]
    shutdown_rows['colour'] = np.nan
    # strip flush/std/startup/shutdown for easier manipulation
    base_df = base_combine_worklists(df1, df2)
    # list of row index nbrs that will have the flush/6-cmpd std; multiple of 10
    list_insert_idx = [*range(10, ceil(base_df.shape[0] / 10)*10, 10)]
    # add 2 every iteration since that is the nbr of rows being added (shift over)
    list_insert_idx = [i+2*e if e != 0 else i for e,
                       i in enumerate(list_insert_idx)]
    # add colour column
    flush_std_rows = df1.iloc[1:3]
    flush_std_rows['colour'] = np.nan
    # insert flush and 6-cmpd std; index the 1st/3rd rows since 0th is startup
    main_df = insert_row_(list_insert_idx, base_df, flush_std_rows.values)
    # add first 3 rows add last three rows
    main_df = pd.concat([startup_rows, main_df, shutdown_rows])
    main_df.reset_index(drop=True, inplace=True)
    return main_df
