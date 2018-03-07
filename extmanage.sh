export DJANGO_SETTINGS_MODULE=ncvoter.local_settings
# trap 'kill %1' SIGINT
postgres -D /Volumes/CalvinNCVdb/postgres/ -p 5455 &
sleep 1 && python manage.py "$@"
kill %1
# trap - SIGINT