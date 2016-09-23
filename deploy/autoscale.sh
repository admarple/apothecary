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

echo "installing python3.4 and some build tools"
yum -y install libffi-devel
yum -y install gcc
yum -y install python34
yum -y install python34-virtualenv

echo "adding user 'apothecary'"
adduser apothecary
chown -R apothecary:apothecary .

echo "setting up virtualenv and installing required packages"
sudo -u apothecary ./.env

echo "starting apothecary with uwsgi"
sudo -u apothecary deploy/start_uwsgi.sh &

echo "installing and starting nginx"
yum -y install nginx
cp deploy/apothecary.conf /etc/nginx/conf.d/
chmod 644 /etc/nginx/conf.d/apothecary.conf
nginx
