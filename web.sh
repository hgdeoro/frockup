#!/bin/bash

BASEDIR=$(cd $(dirname $0); pwd)

. $BASEDIR/virtualenv/bin/activate
export PYTHONPATH=$BASEDIR

python $BASEDIR/frockup/web/index.py
