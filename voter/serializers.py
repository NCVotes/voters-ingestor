from rest_framework import serializers

from voter.models import FileTracker


class FileTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileTracker
        fields = ('created', 'data_file_kind', 'change_tracker_processed',
                  'updates_processed',)

