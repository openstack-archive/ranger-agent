sudo -H pip install -r requirements.txt
sudo python setup.py install
mysql -uroot -pstackdb < ord_db.sql
ord-dbsync
ord-api
ord-engine
