import cx_Oracle
import pandas as pd
import sys
import os
from datetime import datetime
from socket import gethostname

dsn_tns = cx_Oracle.makedsn(ORACLE_HOST,ORACLE_PORT,service_name=ORACLE_SERVNAME)

reg_path = r"Volatile Environment"
reg_key_val = r"WORKLIST_FILEPATH"

    
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

def split_string_input_file(input_file):
    '''handles if contains filepath separator'''
    if '/' in input_file:
        input_file = input_file.split('/')[-1]
    elif '\\' in input_file:
        input_file = input_file.split('\\')[-1]
    return input_file

def imbue_rows(dir_fi, gil_num=gethostname()):
    '''print out each row after extracting data from raw worklist file and then repare for sql entry'''
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
    fi_content_df['plateid'] = fi_content_df['NOTES_STRING[False,68,9]'].apply(lambda x: x.split('/')[1].strip() if not pd.isna(x) else '0') 
    fi_content_df['brooks_barcode'] = fi_content_df['NOTES_STRING[False,68,9]'].apply(lambda x: x.split('/')[0].strip() if not pd.isna(x) else '0')
    
    # get the valid row indices (non-flush/std/shutdown)
    row_idx = grab_rows(fi_content_df)
    
    current_time =  datetime.now().strftime("%Y-%b-%d %H:%M")
    
    with cx_Oracle.connect(ORACLE_USER,ORACLE_PASS,dsn_tns) as con: 
        cursor = con.cursor()
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
                row_data[8] = str(int(float(rdata_df['#Sample Well[True,109,10]'])))
                row_data[9] = rdata_df['#Plate_Sample[True,115,13]']
            except IndexError: 
                 pass #print('passing as a blank ...')
            #print(row_data)
            cursor.execute(f"""insert into GILSON_RUN_LOGS values (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)""", row_data)
        con.commit()
