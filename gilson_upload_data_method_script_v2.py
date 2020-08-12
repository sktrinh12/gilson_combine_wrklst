import xml.etree.ElementTree as ET
import requests
# import winreg
import re
import os
from datetime import datetime
from socket import gethostname


# headers and url for get request & hostname
headers = {'Content-Type': 'application/json'}
url = 'http://10.133.108.219:8003/'
# url = 'http://fr-s-dtp-npsg04/services/v1/chemistry/subfraction'
# url = 'http://localhost:8003/'
hostname = gethostname()

# xml var logs location & original date format
# xml_file_directory = 'C:\\Users\\Tanja\\Documents\\TRILUTION LC 3.0\\Export\\Variable Logs\\'
# orig_date_fmt = '%m/%d/%Y %I:%M:%S %p'
xml_file_directory = '/Users/trinhsk/Documents/'
orig_date_fmt = '%Y-%b-%d %H:%M:%S'

# registry paths to get tsl file path
reg_path = r"Volatile Environment"
reg_key_val = r"WORKLIST_FILEPATH"

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


class RegistryPathDoesNotExist(Exception):
    """Raised when the windows registry couldn't be found"""
    pass


def query_registry(reg_path, reg_key_val):
    access_registry = winreg.ConnectRegistry(
        None, winreg.HKEY_CURRENT_USER)  # If None, the local computer is used
    access_key = winreg.OpenKey(access_registry, reg_path)

    # Read the value.
    result = winreg.QueryValueEx(access_key, reg_key_val)

    # Close the handle object.
    winreg.CloseKey(access_key)
    print(f'>>>registry filepath read: {result[0]}')

    # Return only the value from the resulting tuple (value, type_as_int).
    return result[0]


def check_reg_path_exists(reg_path):
    access_registry = winreg.ConnectRegistry(
        None, winreg.HKEY_CURRENT_USER)  # If None, the local computer is used
    try:
        access_key = winreg.OpenKey(access_registry, reg_path)
        winreg.CloseKey(access_key)
        print(f'>>>registry path exists: {reg_path}')
        return True
    except EnvironmentError:
        print(f'>>>registry path does not exists: {reg_path}')
        return False


def get_rows_xml(root):
    # number of rows of data - 1 for the header
    return len([r for r in root[1][0]]) - 1


def get_xml_text(xmlfile, gilson_number=hostname):
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
                        # have to convert to string bc cannot json serialise
                        # datetime object
                        data_row_dict[f'{row_line}_time'] = datetime.strptime(
                            data.text, orig_date_fmt).strftime('%Y-%b-%d %H:%M:%S')
                    if data_cnt == 1:
                        data_row_dict[f'{row_line}_sample_line'] = int(
                            data.text)
                    if data_cnt == 2:
                        data_row_dict[f'{row_line}_method_name'] = data.text
                    if data_cnt == 3:
                        data_row_dict[f'{row_line}_method_iteration'] = int(
                            data.text)
                    if data_cnt == 4:
                        data_row_dict[f'{row_line}_notes'] = data.text
                    if data_cnt == 5:
                        data_row_dict[f'{row_line}_sample_well'] = int(
                            data.text)
                    if data_cnt == 6:
                        data_row_dict[f'{row_line}_fraction_well'] = int(
                            data.text)
                    if data_cnt == 7:
                        data_row_dict[f'{row_line}_plate_loc'] = data.text
                        data_row_dict[f'{row_line}_gilson_number'] = gilson_number
                data_cnt += 1
        row_line += 1

    return data_row_dict, cnt_rows


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
    # row_data_dict_tosend['xmlfile'] = xmlfile

    # filter dict for jason's endpoint
    for rm_keys in ['method_iteration', 'notes', 'fraction_well']:
        row_data_dict_tosend.pop(rm_keys)

    # rename key names since xml file keys differ from jason's endpoint
    row_data_dict_tosend = rename_key(row_data_dict_tosend,
                                      row_data_dict_tosend.keys(),
                                      new_key_lst)

    for k, v in row_data_dict_tosend.items():
        print(k, v)
    # if check_reg_path_exists(reg_path):
    if True:
        #     row_data_dict_tosend['tsl_filepath'] = query_registry(reg_path, reg_key_val)
        row_data_dict_tosend['TSL_FILEPATH'] = '/Volumes/npsg/tecan/SourceData/SecondStage/Sample List_Combined_tmp/15200300_001_002_comb.tsl'

        # post row data to mongodb
        res = requests.post(url+'es/post/rowdata/', json=row_data_dict_tosend)
        if res:
            print(f'response from server (post data row): {res.text}')
        else:
            print(f'no response form server (post data row)')

        # add task to rq-redis by passing hostname
        res = requests.get(url+f'es/add-task/{hostname}', headers=headers)
        if res:
            print(f'response from server (add task to rq-redis): {res.text}')
        else:
            print(f'no response form server (add task to rq-redis)')

    else:
        raise RegistryPathDoesNotExist("The registry was not found")
