from rest_framework import permissions


class ReadOnlyPermission(permissions.BasePermission):
    """ Only allows read-only HTTP methods."""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
