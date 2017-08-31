source ~/devstack/local.conf &> /dev/null
mysql -uroot -p$MYSQL_PASSWORD < ranger-agent-db.sql &> /dev/null
