import os

from fabric.api import env, local, require, sudo, task

PROJECT_ROOT = os.path.dirname(__file__)


envs = {
    'production': {
        'host_string': 'ec2-35-170-20-68.compute-1.amazonaws.com',
    },
    'staging': {
        'host_string': '',
    },
}


def _common_env():
    env.forward_agent = True
    env.project = 'ncvoter'
    for key, value in envs[env.environment].items():
        setattr(env, key, value)


@task
def staging():
    env.environment = 'staging'
    _common_env()


@task
def production():
    env.environment = 'production'
    _common_env()


@task
def bootstrap():
    """Set up a given environment's Python 2 and RDS database installation for Ansible using Tequila."""
    require('environment')
    local("ansible-playbook -u %s -i deployment/environments/%s/inventory"
          " deployment/playbooks/bootstrap_python.yml" % (env.user, env.environment))
    local("ansible-playbook -u %s -i deployment/environments/%s/inventory"
          " deployment/playbooks/bootstrap_db.yml" % (env.user, env.environment))


@task
def deploy():
    """Deploy to a given environment using Tequila."""
    require('environment')
    local("ansible-galaxy install -i -r deployment/requirements.yml")
    local("ansible-playbook -u %s -i deployment/environments/%s/inventory"
          " deployment/playbooks/site.yml" % (env.user, env.environment))


@task
def manage_shell():
    manage_run('shell')


@task
def manage_run(command):
    """
    Run a Django management command on the remote server.
    """
    require('environment')
    # Setup the call
    manage_sh = u"/var/www/{project}/manage.sh ".format(**env)
    sudo(manage_sh + command, user=env.project)


@task
def supervisor_restart():
    sudo('supervisorctl restart all')


@task
def supervisor_stop():
    sudo('supervisorctl stop all')
