Server Provisioning
========================


Overview
------------------------

The ncvoter project is deployed on the following stack:

- OS: Ubuntu 16.04 LTS
- Python: 3.5
- Database: Postgres 9.6 (RDS)
- Application Server: Gunicorn
- Frontend Server: Nginx
- AWS Region: US-East-1 (N. Virgina)

These services are configured to run on the following machines:

- 1 Application servers (1 AZ, created via CloudFormation and configured via Ansible):
   - Server IPs: `Staging inventory <../deployment/environments/staging/inventory>`_
   - Server IPs: `Production inventory <../deployment/environments/production/inventory>`_
- 1 RDS  instance (created via CloudFormation and managed by AWS)

On the application server, `Supervisord <http://supervisord.org/>`_ manages
the application server process.


AWS Infrastructure
------------------------

Infrastructure for this project is created with the "EC2 Instances, Without NAT Gateway"
option from `AWS Web Stacks <https://github.com/caktus/aws-web-stacks>`_.
A snapshot of the JSON template is saved in this repository at
``deployment/cloudformation-stack.json``.

Before creating a stack you'll need to:

* Determine which AMI to use. You can do this using the `Amazon EC2 AMI Locator <https://cloud-images.ubuntu.com/locator/ec2/>`_ by searching for ``us-east 16.04 hvm ebs ssd``.
* Upload your SSH public key to the EC2 KeyPair section (so you can SSH to the instances after provisioning).

To create a new stack, upload the CloudFormation template via the AWS Console. See the following LastPass entries for variable values:

* Staging: aws-web-stacks: Staging Parameters
* Production: aws-web-stacks: Production Parameters

Other parameters should be self explanatory, or the defaults should be sufficient.

Once CloudFormation begins, you will need to:

* Approve an email sent to the domain admin to accept the AWS::CertificateManager key.
* Add Inbound SSH access to the EC2 instance security group from the Caktus IP.

Fill in the secrets, ``SECRET_KEY`` and ``SECRET_DB_PASSWORD``, in the environment's ``secrets.yml`` file::

  ansible-vault edit deployment/environments/<env>/group_vars/all/secrets.yml

Next, edit ``domain``, ``db_host``, ``SEARCH_HOST`` with the relevant outputs from CloudFormation, and any other relevant environment settings.

Add the web servers to ``deployment/environments/<env>/inventory``.

Add the AWS private key to our SSH keys temporarily::

  ssh-add -K <path-to-key.pem>

Bootstrap the Python environments using the ``ubuntu`` AMI user::

  fab <env> -u ubuntu bootstrap
  fab <env> -u ubuntu deploy

After the initial deploy, you can run the deploy with your user::

  fab <env> deploy


AWS Command Line Interface
__________________________

For more information on how to use the AWS Command Line Interface, please see their `User Guide
<http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html>`_. The following commands
assume:

* You've installed ``awscli`` and ``awslogs`` from ``requirements/deploy.txt``.
* You have ``aws_access_key_id`` and ``aws_secret_access_key`` keys for an AMI account.
* You've configured a ``ncvoter`` `named profile <http://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html>`_ locally.


Disable Autoscaling
~~~~~~~~~~~~~~~~~~~

Since we provision the 2 web instances using Ansible, we don't want autoscaling enabled for this
deployment. To disable, you should suspend the autoscaling processes on the autoscaling group
(after the initial instances are created) since we don't want it to bring up new (unprovisioned)
instances or potentially even terminate one of the instances should it appear unhealthy::

  export AWS_PROFILE=ncvoter
  aws autoscaling suspend-processes --auto-scaling-group-name <your-ag-name>


Viewing Logs via CloudWatch Logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although it's possible to view and search logs via the AWS console, you may find it easier
to do so via the command line, with the (unofficial) ``awslogs`` tool. For example, the following
commands will tail logs from both web servers in the ``staging`` environment::

    export AWS_PROFILE=ncvoter
    export AWS_REGION=us-east-1
    awslogs get staging-/var/log/syslog ALL --watch


Deployment
==========

You can deploy changes to a particular environment with the ``deploy``
command::

    fab staging deploy

New requirements or migrations are detected and will be applied
automatically.

The environments make use of Ansible Vault to protect the server
secrets.  You will need to obtain the vault password from LastPass
(named "NCVotes .vault_pass") and then create a ``.vault_pass`` file at the top
level of this repo that contains it.  Never commit this file to
version control!


Initializing the extra data EBS volume
--------------------------------------

The CF template creates a separate EBS volume to store the large data files.

After attaching the device in the console, first find the name of the device (look for one of the
correct size)::

    fdisk -l

You can also view it using::

  lsblk

If the disk isn't formatted yet, run::

  mkfs.ext4 /dev/<name>
  mkdir /voter-data
  mkdir /voter-data/ncvoter
  mkdir /voter-data/ncvhis
  chown -R root:ncvoter /voter-data/
  chmod -R g+w /voter-data/
  file -s /dev/xvdf

Add to fstab::

  /dev/<name>    /voter-data     ext4    defaults,nofail 0       2

Mount the volume::

  mount -a


Under the hood
--------------

The deployment process is based on `Ansible
<http://docs.ansible.com/ansible/index.html>`_. Your remote
environment will need to have Python 2 installed in order
for Ansible deployment. To ensure this, you can run this one-off
Fabric command::

    fab <environment> bootstrap_python

The deployment setup uses the Caktus `Tequila
roles <https://github.com/caktus/tequila-common>`_.  To install the
needed roles manually, you can run this command::

    $ ansible-galaxy install -i -r deployment/requirements.yml

This command is run automatically by ``fab <environment> deploy``.
The ``-r`` is just like the ``-r`` flag in pip, specifying a file from
which to obtain the list of things to be installed.  The ``-i`` flag
is to ignore errors, which are raised when the roles are already
installed.  The roles from this file are then installed into
``deployment/roles/``, which is the path configured in the
``ansible.cfg`` file at the top level of this repo. This directory is
ignored by the project ``.gitignore``.

The ``ansible-galaxy`` executable has an uninstall command, but it is
often easier to just delete the ``deployment/roles/`` directory.  It
is necessary to uninstall, force install using the ``--force`` or
``-f`` flag, or otherwise delete a role in order to pick up and install
a newer version.

If you have a need to try out changes to the tequila roles before
getting them accepted into the master branch in their repos, you can
remove the specific role directory out of ``deployment/roles/`` and
symlink in your local copy::

    $ rm -rf deployment/roles/tequila-django
    $ cd deployment/roles/
    $ ln -s ~/path/to/tequila-django
    $ cd ../..

To bring up and deploy into a Vagrant box, first bring up the box with
``vagrant up``, then do::

    $ ansible-playbook -i deployment/environments/vagrant/inventory deployment/playbooks/site.yml

or just do ``fab vagrant deploy``.  A version of Vagrant later than
1.8.1 is required, which may be obtained directly as a deb package
from `<http://www.vagrantup.com/>`_.

To deploy into a server environment manually, you can run::

    $ ansible-playbook -i deployment/environments/staging/inventory deployment/playbooks/site.yml --vault-password-file .vault_pass

To be more selective about what is being deployed, choose instead one
of the other playbooks in ``deployment/playbooks/``.


Deployment Configuration
------------------------

The variable files, inventories, and installed Ansible roles are
contained in the ``deployment/`` directory.

``deployment/environments/`` contains a directory for each environment
(currently vagrant and staging).  Each of these has an
inventory file, defining the server or servers involved, and what
roles they fall under.  Additionally, there is a ``group_vars/``
directory for each.  This is where variables that are specific to the
environment are kept.  Variables that need to be kept secret are put
in a ``secrets.yml`` file, which is then encrypted using
ansible-vault.  By convention, variables in the secrets file are
upper-cased, and begin with ``SECRET_``.  These variables are then
referenced in one of the non-encrypted variables files elsewhere in
``deployment/``.

``deployment/playbooks/`` contains the various playbooks, as noted
above.  We currently have one playbook for each server role, and then
a ``site.yml`` playbook which invokes each of the others.  This
directory also contains the variable definitions that are relevant for
the project as a whole, in the ``group_vars/`` directory.  Included
are ``devs.yml`` (for the developer ssh keys), ``project.yml`` (for
the global non-secret variables), and ``secrets.yml`` (for secrets
which do not vary by environment).  Additionally, overridden files and
templates for the Ansible roles belong here.

``deployment/roles/`` is the directory that, by default,
ansible-galaxy will install the required roles for this project.  This
directory may not be present, and can be deleted at any time as a
quick way to uninstall the roles.  Additionally, if one needs to try
out some changes in one of the Tequila roles before they have been
pushed, one can remove its directory from ``deployment/roles/`` and
replace it with a symlink to your local copy of the role.

Finally, there is the ``deployment/requirements.yml`` file.  This file
contains the list of all of the required Ansible roles for this
project.  It is easy enough to change an entry in this file to make
use of a branch for one of the roles instead of master, just replace
the ``src`` like so::

    - src: https://github.com/caktus/tequila-common/archive/my-branch-name.tar.gz


Additional Read-only PostgreSQL Users
-------------------------------------

First create a read-only group (if not already created) as the ``ncvoter`` user::

  -- Create a group
  CREATE ROLE readaccess;

  -- Grant access to existing tables
  GRANT USAGE ON SCHEMA public TO readaccess;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO readaccess;

  -- Grant access to future tables
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readaccess;

From the ``psql`` prompt, now you can run::

  CREATE USER user1 WITH PASSWORD '***';
  GRANT readaccess TO user1;
