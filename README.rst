===============================
Ranger-Agent
===============================

This is used to connect and distribute resources from ranger to Openstack.

Devstack Installation
---------------------
1. You can include ranger-agent repository in `local.conf` when running devstack.
	`enable_plugin ranger-agent git://git.openstack.org/openstack/ranger-agent`

2. Make sure `MYSQL_PASSWORD` is included for creating and accessing the database.


Installation
------------

Clone the repo and go to the `tools` directory.

  $ `git clone https://git.openstack.org/openstack/ranger-agent`

Docker Container:
-----------------

1. $ `cd ranger-agent`

2. $ `sudo docker build -t ranger-agent .`

3. $ `sudo docker run -h "ranger-agent" --net host -it --privileged  ranger-agent  bash`

4. This docker container will be used by helm chart to deploy

Manual:
------

1. $ `cd ranger-agent/tools`

2. Run `./ranger-agent-db.sh` for setting up the database.

3. Run `./withenv.sh`.

4. Run `./run_ranger_agent.sh` and it should have ranger-agent running.

5. If `run_ranger_agent.sh` is not running properly, please do the following:
	1. cd to the root folder.
	2. `source localrc`
	3. `sudo -H pip install -r requirements.txt`
	4. `sudo python setup.py install`
	5. `sudo nohup ord-dbsync > /dev/null 2>&1 &`
	6. `sudo nohup ord-dbsync > /dev/null 2>&1 &`
	7. `sudo nohup ord-engine > /dev/null 2>&1 &`

6. If you want to reinstall and run ranger-agent again, make sure you run `./clear_install_files.sh` to remove previous installation files.
