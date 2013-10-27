#!/bin/bash

echo "Launching web server..."
echo " - to simulate uploads: set 'FROCKUP_DRY_RUN=1'"
echo " - to set max. background (3 by default): set 'FROCKUP_CONCURRENT_UPLOADS=<n>'"
echo ""

BASEDIR=$(cd $(dirname $0); pwd)

. $BASEDIR/virtualenv/bin/activate
export PYTHONPATH=$BASEDIR

python $BASEDIR/frockup/web/index.py
