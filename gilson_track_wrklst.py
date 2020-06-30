import sqlite3
import pandas as pd
import sys
import re
import os
from datetime import datetime
from socket import gethostname
import string
import platform
from random import randint, choice
import winreg
import sys


reg_path = r"Volatile Environment"
reg_key_val = r"WORKLIST_FILEPATH"

def query_registry(reg_path, reg_key_val):
    access_registry = winreg.ConnectRegistry(None,winreg.HKEY_CURRENT_USER) # If None, the local computer is used
    access_key = winreg.OpenKey(access_registry,reg_path)

    # Read the value.                      
    result = winreg.QueryValueEx(access_key, reg_key_val)

    # Close the handle object.
    winreg.CloseKey(access_key)

    # Return only the value from the resulting tuple (value, type_as_int).
    return result[0]

def check_reg_path_exists(reg_path):
    access_registry = winreg.ConnectRegistry(None,winreg.HKEY_CURRENT_USER) # If None, the local computer is used
    try:
        access_key = winreg.OpenKey(access_registry, reg_path)
        winreg.CloseKey(access_key)
        return True
    except EnvironmentError:
        return False


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        #print(sqlite3.version)
        return conn
    except sqlite3.Error as e:
        print(e)

def grab_rows(fi_content_df):
    '''Grab the valid rows from the worklist file'''
    row_idx=[]
    for i in range(fi_content_df.shape[0]):
        try:
            if pd.isna(fi_content_df['#Plate_Sample[True,115,13]'][i]):
                pass#print('nothing')
            else:
                row_idx.append(i)
        except TypeError:
            print(i)
    return row_idx

def blank_barcode():
    '''Create blank barcodes to satisfy the database integrity'''
    blank_bc =  "BLANK_" + ''.join(choice(characters) for x in range(randint(8, 16)))
    return blank_bc

def get_col_names_tbl(table_name, con):
    '''get length of column names and content with indices; returns dictionary'''
    cursor = con.execute(f'SELECT * FROM {table_name} LIMIT 1')
    names = list(map(lambda x: x[0], cursor.description))
    return {'length':len(names),'names':[(i,n) for i,n in enumerate(names)]}

def grab_colm_idx(col_name, con):
    '''returns just the column index that matches the query name'''
    return [i for i,n in get_col_names_tbl("GILSON_TSL_TABLE", con)['names'] if n == col_name][0]

def split_string_input_file(input_file):
    '''handles if contains filepath separator'''
    if '/' in input_file:
        input_file = input_file.split('/')[-1]
    elif '\\' in input_file:
        input_file = input_file.split('\\')[-1]
    return input_file

def imbue_rows(dir_fi, con, commit=False, gil_num=[gethostname()]):
    '''print out each row after extracting data from raw worklist file and then repare for sql entry'''
    nbr = 0
    # check to see if the file path has '/'
    tmp_dir_fi = split_string_input_file(dir_fi)
    split_fi_name = tmp_dir_fi.split('_')
    projectid = split_fi_name[0]
    # read into pandas df and coerce datatypes to string
    fi_content_df = pd.read_csv(dir_fi, sep='\t',dtype={'NOTES_STRING[False,68,9]': str, \
                                                       'SampleId[False,90,5]' : str})
    # ensure strings for each value
    fi_content_df['SampleId[False,90,5]'] = fi_content_df['SampleId[False,90,5]'].apply(lambda x: 'NaN')
    fi_content_df['SampleAmount[False,78,3]'] = fi_content_df['SampleAmount[False,78,3]'].apply(lambda x: f"{str(x)}")
    fi_content_df['#Sample Well[True,109,10]'] = fi_content_df['#Sample Well[True,109,10]'].apply(lambda x: f"{str(x)}")
    # split string and create new column
    fi_content_df['plateid'] = fi_content_df['NOTES_STRING[False,68,9]'].str.split('/').str[1]
    current_col_names = fi_content_df.columns.tolist()[:-1]
    # remove plateid colm as separate list
    plateid_list = [x for x in fi_content_df.plateid.tolist() if not pd.isna(x)]
    # slice df to exlucde plateid
    fi_content_df = fi_content_df[current_col_names]

    # get the valid row indices (non-flush/std/shutdown)
    row_idx = grab_rows(fi_content_df)
    len_rows = len(row_idx)
    # get length of gilson table to import to
    len_cols = get_col_names_tbl('GILSON_TSL_TABLE', con)['length']
    # if not a full set, add blanks 
    if len_rows % 4 != 0:
        len_rows = len_rows + (4-len_rows%4)
    # the index nbr for the blank sample well
    blank_sample_idx = grab_colm_idx('SAMPLE_WELL', con)
    # add random blank barcode
    blank_bc_idx = grab_colm_idx('SAMPLE_DESCRIPTION', con)

    for i in range(len_rows):
        nbr += 1
        row_data = ["BLANK"]*len_cols
        row_data[blank_sample_idx] = nbr
        row_data[2] = projectid
        row_data[0] = nbr
        row_data[-1] = gil_num[0]
        row_data[blank_bc_idx] = blank_barcode()
        try:
            row_data =  list(map(lambda x: str(x), fi_content_df.iloc[row_idx[i]].values.tolist())) + gil_num
            first_4_vals = [str(nbr), datetime.now().strftime("%Y-%b-%d %H:%M"), projectid, plateid_list[i]]
            row_data = first_4_vals + row_data
        except IndexError as e:
             pass#print('passing...')
        if not commit:
            print(row_data)
        if commit:
            con.execute("INSERT INTO GILSON_TSL_TABLE VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row_data)
    if commit:
        con.commit()

if __name__ == "__main__":
    if platform.system() == 'Windows':
        db_file_path = 'N:\\tecan\\SourceData\\SecondStage\\'
    else:
        db_file_path = '/Volumes/npsg/tecan/SourceData/SecondStage/'
        
    if check_reg_path_exists(reg_path):
        result = query_registry(reg_path, reg_key_val)
    else:
        result = 'BLANK' 
        print('registry path does not seem to exist')
        
    if result.endswith('.tsl') and \
            split_string_input_file(result).startswith('15') and \
            os.path.exists(result):
        characters = string.ascii_letters + string.punctuation  + string.digits
        con = create_connection(f"{db_file_path}gilsontsl.db")
        try:
            imbue_rows(sys.argv[1], con, True)
            print('Successfully uploaded worklist to database')
        except sqlite3.Error as e:
            print(f"******ERROR ({e})")
        finally:
            con.close()
    else:
        print(f'not a valid file type or file cannot be found! - {result}')