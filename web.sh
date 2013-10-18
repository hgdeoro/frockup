#!/bin/bash

BASEDIR=$(cd $(dirname $0); pwd)

. $BASEDIR/virtualenv/bin/activate
export PYTHONPATH=$BASEDIR

uwsgi --http-socket 127.0.0.1:3031 --wsgi-file $BASEDIR/frockup/web/index.py --callable app --processes 4 --threads 2 --stats 127.0.0.1:9191
