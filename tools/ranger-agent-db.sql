CREATE DATABASE IF NOT EXISTS ord;
USE ord;
CREATE TABLE IF NOT EXISTS migrate_version (
	repository_id varchar(250) NOT NULL default '',
	repository_path mediumtext NULL,
	version int(11) NULL,
	PRIMARY KEY  (repository_id)
);
CREATE TABLE IF NOT EXISTS ord_notification(
	request_id varchar(50) NOT NULL default '',
  	resource_id varchar(80) NULL,
  	template_type varchar(50) NULL,
  	resource_operation varchar(20) NULL,
  	region varchar(32) NULL,
  	timestamp datetime NULL,
  	PRIMARY KEY  (request_id)
);
CREATE TABLE IF NOT EXISTS target_resource(
  	template_status_id varchar(50) NOT NULL default '',
  	request_id varchar(50) NOT NULL default '',
  	resource_template_version varchar(50) NULL,
  	resource_name varchar(80) NULL,
  	resource_type varchar(50) NULL,
  	status varchar(32) NOT NULL default '',
  	error_code varchar(32) NULL,
  	error_msg varchar(255) NULL,
  	PRIMARY KEY (template_status_id),
	INDEX (request_id)
);
CREATE USER IF NOT EXISTS 'ord'@'%' IDENTIFIED BY 'PASSWORD';
GRANT ALL ON ord.* TO ord;
commit;
