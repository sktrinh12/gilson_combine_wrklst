# Gilson Worklist Combiner 

Automatically generates a `.tsl` worklist file to import into Trilution software to run multiple samples on the GX-180 liquid handler. Contains test code (as Jupyter notebooks `ipynb`) and raw data. 

## Usage

For testing purposes, the use of a `.py` file, called `combine_gilson_worklist_v2.py` is used to combine individual worklists first, then subsequent use of `gilson_track_runs_sqlite3.py` or `gilson_track_runs_oracle.py` to uplaod data to the database. A simple flask app was developed to render the database entires (logging) as html, and also serve an API to upload the data which consist of the core code from `gilson_track_runs_oracle.py`. 

From commman line, type:
```
python combine_gilson_worklist_v2.py ${1} ${2}

```
The two arguments `${1}` and `${2}` would be the two separate worklists generate by the Tecan liquid handler that solubilized samples prior to. The app is dockerized and can be built by entering the command: `docker build -t gilson-logs:latest .` within the directory and then running it using the command: `docker -rm -it --env_file=env_file_name gilson-logs:latest`. 
