source openrc
cd ..
sudo -H pip install -r requirements.txt
sudo python setup.py install
#echo "MYSQL_PASSWORD" < local.conf
#cd tools
MYSQL_PASSWORD=""
source ~/devstack/local.conf &> /dev/null
cd tools
mysql -uroot -p$MYSQL_PASSWORD < ord_db.sql
echo ""
echo "Running ord-dbsync"
sudo ord-dbsync
echo ""
echo "Running ord-api"
sudo ord-api
echo ""
echo "Running ord-engine"
sudo ord-engine
