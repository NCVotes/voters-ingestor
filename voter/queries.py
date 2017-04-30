from datetime import datetime, timezone

from voter.models import FileTracker


def is_etag_a_duplicate(etag):
    return FileTracker.objects.filter(etag=etag).first()


def create_file_track(etag, filename, created_time):
    return FileTracker.objects.create(etag=etag, filename=filename,
                                      created=created_time)

