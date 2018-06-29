from django.contrib import admin

from voter.models import FileTracker, ChangeTracker, NCVoter, NCVHis, BadLineRange, \
    NCVoterQueryView, NCVoterQueryCache


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


@admin.register(NCVoterQueryView)
class NCVoterQueryViewAdmin(admin.ModelAdmin):
    actions = None
    list_display_links = None
    list_display = ('id', 'party_cd', 'county_id', 'race_ethnicity_code', 'status_cd', 'birth_state',
                    'gender_code', 'age', 'res_city_desc', 'zip_code', )
    list_filter = ('party_cd', 'race_ethnicity_code', 'status_cd', 'gender_code', )
    search_fields = ('id', )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NCVoterQueryCache)
class NCVoterQueryCacheAdmin(admin.ModelAdmin):
    list_display = ('qs_filters', 'count')
    search_fields = ('qs_filters', )
