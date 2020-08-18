from db_classes import OracleConnection
from datetime import datetime
import sys


def upload_ordb_rowdata(rowdata_dct, usr, pw, host, port, srv, table_name):
    assert len(rowdata_dct.keys()) == 13,\
        f"The current row data seems empty (or partially), number of values in current row data: {len(rowdata_dct)}, expecting 13 for uploading into oracle table"

    # remove underscore counter for project id
    if '_' in rowdata_dct['PROJECT_ID']:
        rowdata_dct['PROJECT_ID'] = rowdata_dct['PROJECT_ID'].split('_', 1)[0]

    with OracleConnection(usr, pw, host, port, srv) as con:
        sql_stmt = f"""UPDATE {table_name} SET PROJECT_ID = :1,
                        SAMPLE_NAME = :2,
                        BARCODE = :3,
                        BROOKS_BARCODE = :4,
                        PLATE_ID= :5
                            WHERE FINISH_DATE = :6
                            AND GILSON_NUMBER = :7
                            AND PLATE_POSITION = :8"""

        dt = datetime.strftime(
            rowdata_dct['FINISH_DATE'], '%-m/%-d/%Y %-I:%M:%S %p')
        data_lst = [
            rowdata_dct['PROJECT_ID'],
            rowdata_dct['SAMPLE_NAME'],
            rowdata_dct['BARCODE'],
            rowdata_dct['BROOKS_BARCODE'],
            rowdata_dct['PLATE_ID'],
            dt,
            rowdata_dct['GILSON_NUMBER'],
            rowdata_dct['PLATE_POSITION']
        ]

        for d in data_lst:
            print(d)
            sys.stdout.flush()

        assert all([isinstance(d, str) for d in data_lst]), \
            "Can only upload string type values, there are non-string types in the row data"
        with con.cursor() as cursor:
            cursor.execute(sql_stmt, data_lst)
        con.commit()
        print(f'successfully uploaded row data to oracle: {rowdata_dct}')
        sys.stdout.flush()


# def check_in_project_ids(input_project_id):
#     '''Gets the distinct project ids to verify the inputted value is valid usign
#     Oracle'''
#     proj_ids = []
#     with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
#                            app.oracle_dsn_tns) as con:
#         with con.cursor() as cursor:
#             cursor.execute(f"SELECT DISTINCT PROJECT_ID FROM GILSON_RUN_LOGS")
#             proj_ids = cursor.fetchall()
#             proj_ids = [x[0] for x in proj_ids]
#     if input_project_id in proj_ids:
#         return True
#     else:
#         return False


# def query_ordb_curr_row(gilson_number):
#     output = None
#     with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
#                            app.oracle_dsn_tns) as con:
#         with con.cursor() as cursor:
#             cursor.execute(
#                 f"""SELECT TIME_STAMP, NOTES, FRACTION_WELL, PLATE_SAMPLE FROM
#                 {app.config['ORACLE_RT_TABLENAME']} WHERE
#                 gilson_number='{gilson_number}' ORDER BY time_stamp""")
#             output = cursor.fetchone()
#     assert output, f"No current row data fetched from Oracle table, {app.config['ORACLE_RT_TABLENAME']} for GILSON_NUMBER: {gilson_number}"
#     return output


# def get_colnames_ordb():
#     output = None
#     with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
#                            app.oracle_dsn_tns) as con:
#         with con.cursor() as cursor:
#             cursor.execute(
#                 f"select COLUMN_NAME from ALL_TAB_COLUMNS where TABLE_NAME='{app.config['ORACLE_RT_TABLENAME']}'")
#             output = cursor.fetchall()
#     return [cnames[0] for cnames in output]


# def get_tsl_filepath_ordb(gilson_number):
#     output = None
#     with cx_Oracle.connect(app.config['ORACLE_USER'], app.config['ORACLE_PASS'],
#                            app.oracle_dsn_tns) as con:
#         with con.cursor() as cursor:
#             cursor.execute(
#                 f"""select TSL_FILEPATH from {app.config['ORACLE_TSL_FP']} where GILSON_NUMBER = '{gilson_number}'""")
#             output = cursor.fetchone()
#     assert output, f"No filepath fetched from Oracle table, {app.config['ORACLE_TSL_FP']} for GILSON_NUMBER: {gilson_number}"
#     return output[0]
