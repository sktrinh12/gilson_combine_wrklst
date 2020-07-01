from flask import render_template, Markup, request
import os
from functions import *
import cx_Oracle

app = Flask(__name__)

tableName = 'GILSON_RUN_LOGS' 

@app.route('/')
def main():
    with cx_Oracle.connect(ORACLE_USER,ORACLE_PASS,dsn_tns) as con: 
        cursor = con.cursor()
        cursor.execute(f"SELECT * FROM {tableName}")
        output = cursor.fetchall()
    return render_template('index.html', output = output)

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", port=8000)
        
