#!/bin/bash
source localrc

echo Creating database: ord
mysql -uroot -p$MYSQL_PASSWORD < ./ranger-agent-db.sql

echo Done !
