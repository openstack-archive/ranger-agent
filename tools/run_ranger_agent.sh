#! /usr/bin/env bash
source localrc
cd ..
sudo -H pip install -r requirements.txt --proxy $HTTP_PROXY
sudo python setup.py install
echo ""
echo "Running ord-dbsync"
sudo nohup ord-dbsync > /dev/null 2>&1 &
echo ""
echo "Running ord-api"
sudo nohup ord-api > /dev/null 2>&1 &
echo ""
echo "Running ord-engine"
sudo nohup ord-engine > /dev/null 2>&1 &
