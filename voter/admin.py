from django.contrib import admin

from voter.models import FileTracker, ChangeTracker, NCVoter, NCVHis, BadLineRange


@admin.register(FileTracker)
class FileTrackerAdmin(admin.ModelAdmin):
    ordering = ('created',)
    readonly_fields = ('etag', 'filename', 'data_file_kind', 'created')
    list_display = ('short_filename', 'created', 'data_file_kind', 'file_status')


@admin.register(ChangeTracker)
class ChangeTrackerAdmin(admin.ModelAdmin):
    list_display = ('op_code', 'model_name', 'voter', 'election_desc',)
    readonly_fields = ('op_code', 'model_name', 'md5_hash', 'file_tracker',
                       'voter', 'election_desc')


@admin.register(NCVHis)
class NCVHis(admin.ModelAdmin):
    pass


@admin.register(NCVoter)
class NCVoter(admin.ModelAdmin):
    pass


@admin.register(BadLineRange)
class BadLineRangeAdmin(admin.ModelAdmin):
    list_display = ('filename', 'first_line_no', 'last_line_no', 'message')
