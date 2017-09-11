# NC Local Elections Data API

## Project Setup

To setup the project for local development

1. Clone this repo with `git clone git@github.com:reesenewslab/ncvoter.git`
2. Install Python 3.6 and pip
3. Install Postgres (On Mac, you can use `brew install postgres`) . Current
   version in this project is 9.6.2
4. Create a virtualenv with Python 3.6.
5. Activate the virtualenv and install requirements using
   `pip install -r requirements.txt` (from this folder)
6. While you can run `source setupdb.sh` to create and configure Postgres DB
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
7. To create the initially empty database tables, run `python manage.py
   migrate` inside the ncvoter folder where manage.py is.

## Fetching and Processing Data

To fetch the voter data files run `python manage.py voter_fetch`. This will download, unzip and track
any files not already downloaded. Any previously downloaded files that match are simply ignored.

To process and load the data for any existing downloaded files run `python manage.py voter_process`. This
process can take a very long time, especially for the initial import of the files.
