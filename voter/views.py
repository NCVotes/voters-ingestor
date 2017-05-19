from django.http import Http404

from rest_framework.views import APIView
from rest_framework.response import Response

from voter.models import FileTracker
from voter.serializers import FileTrackerSerializer


class FileTrackerList(APIView):

    def get(self, request, format=None):
        file_trackers = FileTracker.objects.all()
        serializer = FileTrackerSerializer(file_trackers, many=True)
        return Response(serializer.data)


class FileTrackerDetail(APIView):

    def get_object(self, pk):
        try:
            return FileTracker.objects.get(pk=pk)
        except FileTracker.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        obj = self.get_object(pk)
        serializer = FileTrackerSerializer(obj)
        return Response(serializer.data)
