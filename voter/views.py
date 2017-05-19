from rest_framework import viewsets


from voter.models import FileTracker
from voter.serializers import FileTrackerSerializer


class FileTrackerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FileTracker.objects.all()
    serializer_class = FileTrackerSerializer
    filter_fields =  ('created', 'data_file_kind', 'change_tracker_processed',
                      'updates_processed',)
