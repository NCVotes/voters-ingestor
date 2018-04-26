# NC Local Elections Data API

[![Build
Status](https://travis-ci.org/NCVotes/voters-ingestor.svg?branch=master)](https://travis-ci.org/NCVotes/voters-ingestor)

## Local Project Setup

### Requirements

* Python >= 3.5
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
5. You can either choose to download and process the full voter files, in which case you'll likely
   need to use a Postgres instance on an external hard drive. Alternatively, you can choose to work
   with a smaller subset of the data. Instructions for both of those alternatives are included
   below.

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
clean up afterwards. For example, to get started, you would do the following steps:

    ./extmanage.sh migrate
    ./extmanage.sh createsuperuser
    ./extmanage.sh runserver

### Local development without an external drive

If you'd prefer not to use an external drive, you may be able to instead use small slices of the
voter files. You will not be able to reproduce the ability of the app to fetch and process full
files, but it may be enough for you to meaningfully work on the application. In order to do this,
download this [zipfile of "sliced" voter
files](https://drive.google.com/file/d/1mc6cSFV5eG533GqAjsJiCyiZdnJ8fzbB/view?usp=sharing).

Unzip the zipfile and record the directory name:

    unzip slices.zip

Create the DB and set it up. This will be in your normal Postgres cluster:

    createdb ncvoter
    python manage.py migrate
    python manage.py createsuperuser

Add the files and begin the processing. The `voter_process_snapshot` step will take a few hours, but
there will be a nice progress bar to watch:

    python manage.py voter_add_files /path/to/dir/slices/
    python manage.py voter_process_snapshot

If you need to stop it, you should be able to abort the process and resume with the `--resume` flag.
Once it's complete, you can run the server and view the data in the admin:

    python manage.py runserver


## Fetching and Processing Data

To fetch the voter data files run `python manage.py voter_fetch`. This will download, unzip and track
any files not already downloaded. Any previously downloaded files that match are simply ignored.

To process and load the data for any existing downloaded files run `python manage.py voter_process`. This
process can take a very long time, especially for the initial import of the files.

Note: make sure that only one `voter_process` is running at any time. Otherwise, conflicts between the processes would result in unexpected behaviors such as issue https://github.com/NCVotes/voters-ingestor/issues/4

After fetching and processing files, clean up can be done with the `voter_drop_files` management
command. When run it will list already processed files. When run with the `--delete` option it will
delete those processed files. It will also show you `FileTrackers` whose files have already been
deleted.

The `--all` option can be given to delete all files, even those which have not yet been processed.


## Deployment

$ fab production deploy

### FIXME

- need to add 'apt install unzip' since we need that package installed
