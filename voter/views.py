from rest_framework import viewsets
import django_filters


from voter.models import FileTracker
from voter.serializers import FileTrackerSerializer


class FileTrackerFilterSet(django_filters.FilterSet):
    created = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = FileTracker
        fields = ('created', 'data_file_kind', 'change_tracker_processed',
                  'updates_processed',)


class FileTrackerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FileTracker.objects.all()
    serializer_class = FileTrackerSerializer
    filter_class = FileTrackerFilterSet
