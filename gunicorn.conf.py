# Gunicorn Production Configuration File
# Run using: gunicorn -c gunicorn.conf.py Project_goatfarm:app

import multiprocessing

# 1. Server Socket Binding
bind = "127.0.0.1:5001"
backlog = 2048

# 2. Worker & Thread Management (Prevent DoS, match server capacity)
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
worker_connections = 1000
timeout = 30
keepalive = 2

# 3. Security Limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 4. Logging & Auditing
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
access_log_format = '%({x-correlation-id}i)s %(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 5. Process Management
daemon = False
pidfile = "/run/gunicorn/ranga_farm.pid"
user = "appuser"
group = "appgroup"
umask = 0o007
