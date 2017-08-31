#! /usr/bin/env bash
source openrc
cd ..
sudo -H pip install -r requirements.txt
sudo python setup.py install
echo ""
echo "Running ord-dbsync"
sudo ord-dbsync
echo ""
echo "Running ord-api"
sudo ord-api
echo ""
echo "Running ord-engine"
sudo ord-engine
