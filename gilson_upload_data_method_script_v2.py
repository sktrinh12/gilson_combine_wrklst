import xml.etree.ElementTree as ET
import requests
import re
import os
# from datetime import datetime
from random import randint


# headers and url for get request & hostname
headers = {'Content-Type': 'application/json'}
# url = 'http://10.133.108.219:8003/'
url = 'http://localhost:8003/'
# hostname = f'GILSON_{randint(1,8)}'
hostname = 'Tecan6'

# xml var logs location & original date format
# orig_date_fmt = '%m/%d/%Y %I:%M:%S %p'
xml_file_directory = '/Volumes/npsg/Gilson/Scripts/test_xmls'
# xml_file_directory = '/Volumes/npsg/Gilson/Scripts'

new_key_lst = ["FINISH_DATE",
               "SEQ_NUM",
               "METHOD_NAME",
               "SAMPLE_WELL",
               "PLATE_POSITION",
               "GILSON_NUMBER",
               ]


def rename_key(iterable, old_key_lst, new_key_lst):
    dct = {}
    len_new_kl = len(new_key_lst)
    len_old_kl = len(old_key_lst)
    assert len_new_kl == len_old_kl, "key lists must be same length - old key list length : {len_old_kl}, new key list length: {len_new_kl}"
    # for nk, ok in zip(new_key_lst, old_key_lst):
    #     print(nk, ok)
    if type(iterable) is dict:
        for n_k, o_k in zip(new_key_lst, old_key_lst):
            # iterable[n_k] = iterable.pop(o_k)
            dct[n_k] = iterable[o_k]
    return dct


def get_xml_text(xmlfile, gilson_number=hostname):
    tree = ET.parse(xmlfile)
    root = tree.getroot()
    data_row_dict = dict()
    ws = root.find('{urn:schemas-microsoft-com:office:spreadsheet}Worksheet')
    row_cnt = 0
    for i, rw in enumerate(ws[0]):  # table
        if i == 0:  # skip the header
            pass
        else:
            row_cnt += 1
            for j, cell in enumerate(rw):  # each cell of row
                for data in cell:  # each data value of cell
                    if j == 0:
                        data_row_dict[f'{i}_time'] = data.text
                    if j == 1:
                        data_row_dict[f'{i}_sample_line'] = int(
                            data.text)
                    if j == 2:
                        data_row_dict[f'{i}_method_name'] = data.text
                    if j == 3:
                        data_row_dict[f'{i}_method_iteration'] = int(
                            data.text)
                    if j == 4:
                        data_row_dict[f'{i}_notes'] = data.text
                    if j == 5:
                        data_row_dict[f'{i}_sample_well'] = int(
                            data.text)
                    if j == 6:
                        data_row_dict[f'{i}_fraction_well'] = int(
                            data.text)
                    if j == 7:
                        data_row_dict[f'{i}_plate_loc'] = data.text
                        data_row_dict[f'{i}_gilson_number'] = gilson_number
    return data_row_dict, row_cnt

# def get_xml_text(xmlfile, gilson_number=hostname):
#     tree = ET.parse(xmlfile)
#     root = tree.getroot()
#     cnt_rows = get_rows_xml(root)
#     data_row_dict = dict()
#     row_line = 0
#     for row in root[1][0]:
#         data_cnt = 0
#         for cell in row:
#             if cell.items()[0][1] == "NormalStyle":
#                 for data in cell:
#                     if data_cnt == 0:
#                         # have to convert to string bc cannot json serialise
#                         # datetime object
#                         data_row_dict[f'{row_line}_time'] = datetime.strptime(
#                             data.text, orig_date_fmt).strftime('%Y-%b-%d %H:%M:%S')
#                     if data_cnt == 1:
#                         data_row_dict[f'{row_line}_sample_line'] = int(
#                             data.text)
#                     if data_cnt == 2:
#                         data_row_dict[f'{row_line}_method_name'] = data.text
#                     if data_cnt == 3:
#                         data_row_dict[f'{row_line}_method_iteration'] = int(
#                             data.text)
#                     if data_cnt == 4:
#                         data_row_dict[f'{row_line}_notes'] = data.text
#                     if data_cnt == 5:
#                         data_row_dict[f'{row_line}_sample_well'] = int(
#                             data.text)
#                     if data_cnt == 6:
#                         data_row_dict[f'{row_line}_fraction_well'] = int(
#                             data.text)
#                     if data_cnt == 7:
#                         data_row_dict[f'{row_line}_plate_loc'] = data.text
#                         data_row_dict[f'{row_line}_gilson_number'] = gilson_number
#                 data_cnt += 1
#         row_line += 1

    # return data_row_dict, cnt_rows


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
    assert files, f"No XML file found given search constraints in {xml_file_directory}"
    print(f'>>>newest xml file found: {files[0]}')
    return files[0]


if __name__ == "__main__":
    xmlfile = get_newest_xmlfile(xml_file_directory)
    row_data_dict_tosend, row_cnt = get_xml_text(xmlfile)
    # remove the 'index_' at beginning of key
    row_data_dict_tosend = {k[2:]: v for k, v in row_data_dict_tosend.items()}

    # filter dict for NPSG's endpoint
    for rm_keys in ['method_iteration', 'notes', 'fraction_well']:
        row_data_dict_tosend.pop(rm_keys)

    # rename key names since xml file keys differ from jason's endpoint
    row_data_dict_tosend = rename_key(row_data_dict_tosend,
                                      row_data_dict_tosend.keys(),
                                      new_key_lst)

    row_data_dict_tosend['TSL_FILEPATH'] = '/Volumes/npsg/tecan/SourceData/SecondStage/Sample List_Combined_tmp/1578_test.tsl'

    for k, v in row_data_dict_tosend.items():
        print(k, v)

    try:
        res = requests.post(url+'es/post/rowdata',
                            json=row_data_dict_tosend)
        print(f'response from server (post data row): {res.text}')
    except requests.exceptions.RequestException as e:
        print(f'no response form server (post data row) - {e}')
