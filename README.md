# NC Local Elections Data API

## Local Project Setup

### Requirements

* Python >= 3.6
* Postgres >= 9.6
* pip >= 9.0.1
* virtualenv >= 15.0.1

### Set up

1. Clone this repo with `git clone git@github.com:NCVotes/voters-ingestor.git`
2. Create a virtualenv with Python 3.6.
3. Activate the virtualenv and install local requirements using
   `pip install -r requirements/dev.txt` (from this folder)
4. Copy `ncvoter/local_settings.example.py` to `ncvoter/local_settings.py` and
   customize for your machine.
4. While you can run `source setupdb.sh` to create and configure Postgres DB
   for the project, you may need to consider if the database can fit on the
   hard disk you're working with. By default, postgres will use the drive it is
   installed on.  If you intend to use an external or non-default drive, the
   setupdb.sh script takes an optional argument for a PostgreSQL TABLESPACE
   location. This argument is a fully qualified path to a folder on the
   external volume where you've created a folder for Postgres to use. E.g.
   /Volumes/SEAGATE/ncvoter-db. As an example, to use that folder for
   PostgreSQL storage, run `source setupdb.sh /Volumes/SEAGATE/ncvoter-db`.
   This script can be run at any later time, but any existing data will be
   deleted.
5. To create the initially empty database tables, run `python manage.py
   migrate` inside the ncvoter folder where manage.py is.

### External Database Drive Tips

Are you running the project with a database sitting on an external drive? Here
are some tips for workflows that make this process easier.

#### Creating an external database

You can move only one database on your postgres instance to a different drive,
but you can't stop and start single databases. This means simply moving the TABLESPACE
would still leave you with problems when disconnecting the external drive.

Instead, create a whole separate cluster and run a separate postgres instance *only*
when working on this project. We'll set the PGDATA variable to point to your external
volume. Make sure to add that variable to your .bashrc or your
$VIRTUAL_ENV/bin/postactivate script. All of the other Postgres commands in these instructions
assume that it has been set.

    export PGDATA=/Volumes/CalvinNCVdb/postgres
    pg_ctl initdb

Note for Ubuntu users: pg_ctl is not in your PATH by default on Ubuntu. You can
add it yourself. Obviously, change the Postgres version to the version you have.

    export PATH=$PATH:/usr/lib/postgresql/9.6/bin/

You can append this line to your .bashrc (or $VIRTUAL_ENV/bin/postactivate) if you want it available
all the time.

    echo "export PATH=$PATH:/usr/lib/postgresql/9.6/bin/" >> .bashrc

#### Starting and stopping an external database

Because you are only running this instance of PG when working on this project, it
will be best to run it in the foreground in one of your terminals. This will make it
easier to remember its there and running, so that you can terminate it before
disconnecting the drive.

To run the external postgres in a terminal, using post 5455:

    postgres -p 5455

To stop the external postgres, simply terminate the command with Ctrl+C in the same terminal.

Notice that we need to run this on a non-default port, so you'll need to set the appropriate
port number you use in your django settings.

#### Managing databases on the external instance

Common commands like `createdb` and `dropdb` connect via default options, so they won't
operate on your external instance. Simply use the `-p` option to any of them.

    createdb -p 5455 ncvoter

Of course, because the Postgres instance runs in the foreground, you'll need to leave it
running in one terminal and run these commands in another.

#### Running Django commands easily

A helper script is included to start up the external DB to run a manage.py command. Simply
replace `./manage.py` with `./extmanage.sh` to run a command with the DB running, and automatically
clean up afterwards.

## Fetching and Processing Data

To fetch the voter data files run `python manage.py voter_fetch`. This will download, unzip and track
any files not already downloaded. Any previously downloaded files that match are simply ignored.

To process and load the data for any existing downloaded files run `python manage.py voter_process`. This
process can take a very long time, especially for the initial import of the files.

Note: make sure that only one `voter_process` is running at any time. Otherwise, conflicts between the processes would result in unexpected behaviors such as issue https://github.com/NCVotes/voters-ingestor/issues/4
