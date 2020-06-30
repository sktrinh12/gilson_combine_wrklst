#Gunicorn configuration file
from multiprocessing import cpu_count
bind = '0.0.0.0:8000'
backlog = 2048
workers = cpu_count() 
worker_class = 'sync'
worker_connections = 1000
timeout = 120 
keepalive = 24 * 60
spew = False
daemon = False
dfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None
pidfile = None
errorlog = '-'
loglevel = 'info'
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
proc_name = None
