CREATE DATABASE IF NOT EXISTS ord; 
USE ord;
CREATE USER 'ord'@'%' IDENTIFIED BY 'PASSWORD';
GRANT ALL ON ord.* TO ord;
commit;
