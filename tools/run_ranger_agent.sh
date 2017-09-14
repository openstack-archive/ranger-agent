#! /usr/bin/env bash
cd ..
sudo -H pip install -r requirements.txt --proxy $HTTP_PROXY
sudo python setup.py install
echo ""
echo "Running ord-dbsync"
nohup ord-dbsync > /dev/null 2>&1 &
echo ""
echo "Running ord-api"
nohup ord-api > /dev/null 2>&1 &
echo ""
echo "Running ord-engine"
nohup ord-engine > /dev/null 2>&1 &
