#!/bin/bash

cd /source
#jupyter notebook --allow-root --ip 0.0.0.0 &
uwsgi --ini /source/wsgi.ini
nginx &

# Wait for uwsgi.log file init
sleep 1

tail -f /source/uwsgi.log

sleep infinity
