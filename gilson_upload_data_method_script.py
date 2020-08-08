import xml.etree.ElementTree as ET
import requests
import winreg
import re
import os
import cx_Oracle
from datetime import datetime, timedelta
from socket import gethostname

ORACLE_HOST = "DTPIV1.NCIFCRF.GOV"
ORACLE_PORT = 1523
ORACLE_SERVNAME = "PROD.NCIFCRF.GOV"
ORACLE_PASS = "P2wC9Gq3r4"
ORACLE_USER = "NPSG"

dsn_tns = cx_Oracle.makedsn(
    ORACLE_HOST, ORACLE_PORT, service_name=ORACLE_SERVNAME)

# headers and url for get request & hostname
headers = {'Content-Type': 'application/json'}
url = 'http://0.0.0.0:8003/es/add-task/'
hostname = gethostname()

# xml var logs location & original date format
xml_file_directory = 'C:\\Users\\Tanja\\Documents\\TRILUTION LC 3.0\\Export\\Variable Logs\\'
orig_date_fmt = '%m/%d/%Y %I:%M:%S %p'
# xml_file_directory = '/Users/trinhsk/Documents/'
# orig_date_fmt = '%Y-%b-%d %H:%M:%S'

# registry paths to get tsl file path
reg_path = r"Volatile Environment"
reg_key_val = r"WORKLIST_FILEPATH"

# oracle tables
oracle_table_fp = 'GILSON_WORKLIST_FILEPATH'
oracle_table_rtlogs = 'GILSON_RT_VAR_LOGS'


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

    # Return only the value from the resulting tuple (value, type_as_int).
    return result[0]


def check_reg_path_exists(reg_path):
    access_registry = winreg.ConnectRegistry(
        None, winreg.HKEY_CURRENT_USER)  # If None, the local computer is used
    try:
        access_key = winreg.OpenKey(access_registry, reg_path)
        winreg.CloseKey(access_key)
        return True
    except EnvironmentError:
        return False


def check_gilson_nbr_exist_ordb(cursor):
    '''check if there is a record for the asking gilson number; if so; then will
    return True and update the filepath'''
    cursor.execute(f"""SELECT * FROM {oracle_table} WHERE
                   GILSON_NUMBER = '{hostname}'""")
    result = cursor.fetchone()
    if result:
        return True
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
                        data_row_dict[f'{row_line}_time'] = datetime.strptime(
                            data.text, orig_date_fmt)
                    if data_cnt == 1:
                        data_row_dict[f'{row_line}_sample_line'] = int(
                            data.text)
                    if data_cnt == 2:
                        data_row_dict[f'{row_line}_method_name'] = data.text
                    if data_cnt == 3:
                        data_row_dict[f'{row_line}_method_iterion'] = int(
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
    return files[0]


if __name__ == "__main__":
    ddict, row_cnt = get_xml_text(get_newest_xmlfile(xml_file_directory))
    dlist = [v for k, v in ddict.items() if k.startswith(f'{row_cnt}')]
    print(dlist)
    if check_reg_path_exists(reg_path):
        filepath = query_registry(reg_path, reg_key_val)
        with cx_Oracle.connect(ORACLE_USER, ORACLE_PASS, dsn_tns) as con:
            with con.cursor() as cursor:
                check = check_gilson_nbr_exist_ordb(cursor)
                # upload TSL FILEPATH to ORACLE
                if check:
                    cursor.execute(
                        f"""UPDATE {oracle_table_fp} SET TSL_FILEPATH = '{filepath}', GILSON_NUMBER = '{hostname}'""")
                    print(
                        f'updated new row of data into ({oracle_table_fp}) for {hostname}')
                else:
                    cursor.execute(
                        f"""INSERT INTO {oracle_table_fp} (TSL_FILEPATH, GILSON_NUMBER) VALUES ('{filepath}', '{hostname}')""")
                    print(
                        f'inserted new row of data into ({oracle_table_fp}) for {hostname}')
                if dlist:
                    # upload XML row data to ORACLE
                    cursor.execute(
                        f"""INSERT INTO {oracle_table_rtlogs} (TIME_STAMP, SAMPLE_LINE,
                            METHOD_NAME, METHOD_ITERATION, NOTES, SAMPLE_WELL,
                            FRACTION_WELL, PLATE_SAMPLE, GILSON_NUMBER) VALUES
                            (:1, :2, :3, :4, :5, :6, :7, :8, :9)""", dlist)
            con.commit()
        print(
            'inserted new row of data into ORACLE table ({oracle_table_rtlogs})')
        r = requests.get(url+hostname, headers=headers)
        print(r.content)
    else:
        raise RegistryPathDoesNotExist("The registry was not found")
