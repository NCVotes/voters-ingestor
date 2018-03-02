# NC Local Elections Data API

[![Build
Status](https://travis-ci.org/NCVotes/voters-ingestor.svg?branch=master)](https://travis-ci.org/NCVotes/voters-ingestor)

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

## Fetching and Processing Data

To fetch the voter data files run `python manage.py voter_fetch`. This will download, unzip and track
any files not already downloaded. Any previously downloaded files that match are simply ignored.

To process and load the data for any existing downloaded files run `python manage.py voter_process`. This
process can take a very long time, especially for the initial import of the files.

Note: make sure that only one `voter_process` is running at any time. Otherwise, conflicts between the processes would result in unexpected behaviors such as issue https://github.com/NCVotes/voters-ingestor/issues/4
