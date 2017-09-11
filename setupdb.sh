

if [ -z "$1" ]; then
    echo "Creating ncvoter database without a TABLESPACE"
else
    echo "Creating ncvoter database with the ncvoter TABLESPACE at" "$1"
fi

psql postgres -c "DROP DATABASE if exists ncvoter;"
psql postgres -c "DROP DATABASE if exists test_ncvoter"
psql postgres -c "DROP TABLESPACE if exists ncvoter;"

if [ "$1" ]; then
    psql postgres -c "CREATE TABLESPACE ncvoter LOCATION '"$1"'"
    psql postgres -c "CREATE DATABASE ncvoter WITH ENCODING 'UTF8' TABLESPACE ncvoter;"
else
    psql postgres -c "CREATE DATABASE ncvoter WITH ENCODING 'UTF8';"
fi

psql postgres -c "DROP ROLE IF EXISTS ncvoter;
                    CREATE USER ncvoter WITH PASSWORD '';
                    ALTER ROLE ncvoter SET default_transaction_isolation TO 'read committed';
                    ALTER ROLE ncvoter SET timezone TO 'UTC';
                    ALTER USER ncvoter CREATEDB;
                    GRANT ALL PRIVILEGES ON DATABASE ncvoter TO ncvoter;"
