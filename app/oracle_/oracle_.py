from functions import *
from flask import current_app as app
import cx_Oracle
import sys
sys.path.insert(0, '..')


def check_in_project_ids(input_project_id):
    '''Gets the distinct project ids to verify the inputted value is valid usign
    Oracle'''
    with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
                           app.oracle_dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(f"SELECT DISTINCT PROJECT_ID FROM GILSON_RUN_LOGS")
        proj_ids = cursor.fetchall()
    proj_ids = [x[0] for x in proj_ids]
    if input_project_id in proj_ids:
        return True
    else:
        return False


# def get_column_names_db(cursor):
#     cursor.execute(
#         "SELECT column_name FROM all_tab_cols WHERE table_name = 'GILSON_RUN_LOGS'")
#     output = cursor.fetchall()
#     return [_[0] for _ in output]


def query_ordb_curr_row(gilson_number):
    output = None
    with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
                           app.oracle_dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(
            f"""SELECT TIME_STAMP, NOTES, FRACTION_WELL, PLATE_SAMPLE FROM
            {app.config['ORACLE_RT_TABLENAME']} WHERE
            gilson_number='{gilson_number}' ORDER BY time_stamp""")
        output = cursor.fetchone()
    assert output, f"No data queried from Oracle table, {app.config['ORACLE_RT_TABLENAME']} for GILSON_NUMBER: {gilson_number}"
    return output


def get_colnames_ordb():
    output = None
    with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
                           app.oracle_dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(
            f"select COLUMN_NAME from ALL_TAB_COLUMNS where TABLE_NAME='{app.config['ORACLE_RT_TABLENAME']}'")
        output = cursor.fetchall()
    return [cnames[0] for cnames in output]


def get_tsl_filepath_ordb(gilson_number):
    output = None
    with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
                           app.oracle_dsn_tns) as con:
        cursor = con.cursor()
        cursor.execute(
            f"""select TSL_FILEPATH from {app.config['ORACLE_TSL_FP']} where GILSON_NUMBER = '{gilson_number}'""")
        output = cursor.fetchone()
    assert output, f"No data queried from Oracle table, {app.config['ORACLE_TSL_FP']} for GILSON_NUMBER: {gilson_number}"
    return output[0]
