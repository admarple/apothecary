#!/bin/sh

# This script is intended to be run as root when an EC2 instance is provisioned
# There is some bootstrapping required to pull apothecary from github, e.g.
#   mkdir -p /opt/app/
#   chmod 755 /opt/app
#   cd /opt/app
#   yum -y install git
#   git clone https://github.com/admarple/apothecary.git
#   cd apothecary
#   ./deploy/autoscale.sh

# install python3 and some build tools
yum -y install libffi-devel
yum -y install gcc
yum -y install python34
yum -y install python34-virtualenv

adduser apothecary
chown -R apothecary .

su - apothecary
# setup virtualenv and install required packages
./.env
# start apothecary as a uwsgi application
uwsgi -s /tmp/uwsgi.sock --manage-script-name --mount /=apothecary:app --virtualenv ./venv
exit

# start nginx
yum -y install nginx
cp deploy/apothecary.conf /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/apothecary.conf
nginx
