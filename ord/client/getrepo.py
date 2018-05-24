#  Copyright 2016 ATT
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import ord.common.exceptions as excp
import os
import shlex
import subprocess

from ord.openstack.common import log as logging
from oslo_config import cfg
from oslo_utils import fileutils


CONF = cfg.CONF
ORM_OPTS = [
    cfg.StrOpt('orm_template_repo_url',
               default='',
               help='Remote repo location'),
    cfg.Opt('repo_pull_check_wait',
            default='1',
            help='Wait Time'),
    cfg.IntOpt('resource_status_check_wait', default=15,
               help='delay in seconds between two retry call'),
    cfg.IntOpt('retry_limits',
               default=5,
               help='number of retry'),
]

cfg.CONF.register_opts(ORM_OPTS, group='orm')
LOG = logging.getLogger(__name__)
subprocess._has_poll = False


class TemplateRepoClient(object):

    """Implementation to download template from repo.

    Requires minimal installation (git) and minimal upkeep.
    """

    def __init__(self, local_repo):
        """Clone git repo."""
        self.git_repo_status = False
        self.git_init_repo(local_repo)

    def git_init_repo(self, local_repo):

        # Check if local git repo already exists
        repopath = os.path.join(os.environ['HOME'], local_repo)

        repo = cfg.CONF.orm.orm_template_repo_url
        LOG.info(
            "%s Setting up repo initiated ...", os.path.basename(repo))

        # create the git repo directory if not exists
        fileutils.ensure_tree(repopath)
        try:
            # initialize repo directory as a git repo
            cmd = 'git init {0}'.format(repopath)
            self.run_git('GitRepoInit', cmd, workdir=repopath)
            try:
                # set remote origin
                cmd = 'git -C {0} remote add origin {1}'.format(
                    repopath, repo)
                self.run_git('GitRepoInit', cmd, workdir=repopath)
            except Exception as repoexp:
                pass
            # fetch origin
            rem_lock_file = '{0}/.git/refs/remotes/origin/master.lock'\
                .format(repopath)
            if os.path.exists(rem_lock_file):
                os.remove(rem_lock_file)
            cmd = 'git -C {0} fetch origin'.format(
                repopath)
            self.run_git('GitRepoInit', cmd, workdir=repopath)
        except Exception as repoexp:
            self.git_repo_status = False
            LOG.critical("Failed to initialize Repo %s " % repoexp)
        LOG.info(
            "%s Setting up repo status (completed = %s)",
            os.path.basename(repo), self.git_repo_status)

    def pull_template(self, local_repo, pathtotemplate):
        """Get template from repo.
        :param local_repo: local repo name
        :param pathtotemplate: path to template
        """
        if not self.git_repo_status:
            self.git_init_repo(local_repo)

        LOG.debug("Template pull initiated ...")
        workdir = os.path.join(os.environ['HOME'], local_repo)

        # normalize the path before checking if file exists
        templatepath = os.path.normpath(
            os.path.join(workdir, pathtotemplate))
        # delete previous version
        if os.path.isfile(templatepath):
            os.remove(templatepath)

        cmd = 'git -C {0} checkout FETCH_HEAD  -- {1}'.format(
            workdir, pathtotemplate)
        self.run_git('PullTemplate', cmd, workdir=workdir, is_timeout=True)

        LOG.debug("Template pull completed ...")

        return templatepath

    def run_git(self, label, cmd, workdir=None, is_timeout=False):
        LOG.info("Running cmd: '%s'", cmd)
        timed_out = False
        retry_left = CONF.orm.retry_limits

        if is_timeout:
            timeout_sec = cfg.CONF.resource_status_check_wait
            cmd = 'timeout -k {0}s {1}s {2}'.format(timeout_sec + 5,
                                                    timeout_sec, cmd)
            LOG.info('Setting cmd timeout to: %s seconds', timeout_sec)

        while(retry_left > 0):
            try:
                process = subprocess.Popen(
                    shlex.split(cmd), stdout=subprocess.PIPE,
                    shell=False, stderr=subprocess.PIPE)

                [stdout, stderr] = process.communicate()

                # 124 is the return code in the shell if timeout occurred
                if process.returncode == 124:
                    timed_out = True
                    LOG.critical(
                        "Run command '%s' exceeded the alloted"
                        "time of %s seconds, process was killed.",
                        cmd, timeout_sec)

            except Exception as exception:
                LOG.critical("Unexpected error running '%s'"
                             "exception: %s",
                             cmd, exception.args)
                [stdout, stderr] = process.communicate()

            finally:
                proc_result = {}
                proc_result["returncode"] = process.returncode
                proc_result["stdout"] = stdout.decode("UTF-8")
                proc_result["stderr"] = stderr.decode("UTF-8")
                proc_result["timed_out"] = timed_out

                if proc_result["returncode"] == 0:
                    retry_left = 0
                    process.returncode = 0
                    self.git_repo_status = True
                else:
                    if 'remote origin already exists' in proc_result["stderr"]:
                        retry_left = 0
                    else:
                        retry_left -= 1
                    LOG.warning("stderr: %s", proc_result)
                    LOG.warning("Retrying cmd '%s'. Retries left: %s",
                                cmd, retry_left)
                    if workdir is not None:
                        try:
                            rem_lock_file = '{0}/.git/refs/remotes/origin/master.lock'\
                                .format(workdir)
                            if os.path.exists(rem_lock_file):
                                os.remove(rem_lock_file)
                            fetch = 'git -C {0} fetch origin'.format(workdir)
                            fetch_process = subprocess.Popen(
                                shlex.split(fetch), stdout=subprocess.PIPE,
                                shell=False, stderr=subprocess.PIPE)
                            [stdout, stderr] = fetch_process.communicate()
                            LOG.info("Run command '%s' to syncup"
                                     " repo after error", fetch)
                        except Exception:
                            pass

        if process.returncode != 0:
            self.check_git_errors(label, proc_result)

    def check_git_errors(self, label, result):
        stderr = result['stderr'].lower()

        if result['timed_out']:
            raise excp.RepoTimeoutException(label=label)

        elif 'service not known' in stderr:
            raise excp.RepoIncorrectURL(label=label)

        elif 'does not exist' in stderr:
            raise excp.RepoNotExist(label=label)

        elif ('permission denied' in stderr) or ('No such remote' in stderr):
            raise excp.RepoNoPermission(label=label)

        elif 'did not match any file(s) known to git' in stderr:
            raise excp.FileNotInRepo(label=label)

        elif 'remote origin already exists' in stderr:
            pass
        else:
            # general unknown exception in case none of the above
            # are the cause of the problem
            raise excp.RepoUnknownException(label=label, unknown=stderr)
