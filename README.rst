===============================
Ranger-Agent
===============================

This is the ranger-agent project. At the highest view, provides an API interface
for users to move OpenStack templates from CodeCloud into OS Heat.

This project is designed to show a recommended set of modules
for creating a simple API server and Engine, with a versioned API, clean separation
of modules, a standard way of structuring both unit and functional tests,
configuration files, and documentation.

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
   Creating docker image and publish will be done by CICD jobs.For Refernce and validation manually image could push using..
   a). $ `docker login <docker_user_id>`
   b). $ `docker tag ranger-agent <docker_user_id>/ranger-agent:0.1.0`
   c). $ `docker push <docker_user_id>/ranger-agent:0.1.0`

4. This docker container will be used by helm chart to deploy

Manual:
------

1. $ `cd ranger-agent/tools`

2. Run `./ranger-agent-db.sh` for setting up the database.

3. Run `./with_venv.sh`.

4. Run `./run_ranger_agent.sh` and it should have ranger-agent running.

5. If `run_ranger_agent.sh` is not running properly, please do the following:
	1. cd to the root folder.
	2. `source localrc`
	3. `sudo -H pip install -r requirements.txt`
	4. `sudo python setup.py install`
	5. `sudo nohup ord-dbsync > /dev/null 2>&1 &`
	6. `sudo nohup ord-engine > /dev/null 2>&1 &`

6. If you want to reinstall and run ranger-agent again, make sure you run `./clear_install_files.sh` to remove previous installation files.

