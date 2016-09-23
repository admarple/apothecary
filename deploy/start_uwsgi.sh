#!/bin/sh
# start uwsgi in the virtualenv
#
# Why a script just for this?  Because I'd like to be able to run uwsgi
#  * as user apothecary
#  * after sourcing the virtualenv
#  * in the background
#
# Sourcing then sudo-ing doesn't preserve the virtual env.
# sudo with "&&" or ";" results in sudo-ing the virtual env activation, then running uwsgi without
# 'sudo -c sh "..."' runs uwsgi in the virtualenv, but the "&" for running in the background
#    is passed to sh, which runs in the foreground
# This script preserves the virtualenv for uwsgi, but it can be run in the background

source venv/bin/activate
uwsgi \
  -s /tmp/apothecary.sock \
  --manage-script-name \
  --mount /=apothecary:app \
  --virtualenv ./venv \
  --chmod-socket=766
