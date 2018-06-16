import logging
import os
import random
from datetime import datetime
import pytz

from django.db import connection, models, transaction
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.serializers.json import DjangoJSONEncoder

from ncvoter.known_cities import KNOWN_CITIES
from voter.constants import GENDER_FILTER_CHOICES, PARTY_FILTER_CHOICES, RACE_FILTER_CHOICES

logger = logging.getLogger(__name__)


class FileTracker(models.Model):

    class Meta:
        verbose_name = "File Tracker"
        verbose_name_plural = "File Tracking"

    DATA_FILE_KIND_NCVOTER = 'NCVoter'
    DATA_FILE_KIND_NCVHIS = 'NCVHis'
    DATA_FILE_KIND_CHOICES = [
        (DATA_FILE_KIND_NCVHIS, 'NCVHis file'),
        (DATA_FILE_KIND_NCVOTER, 'NCVoter file'),
    ]

    UNPROCESSED = 0
    PROCESSING = 1
    PROCESSED = 2
    CANCELLED = 3
    STATUS_CHOICES = [
        (UNPROCESSED, 'Unprocessed'),
        (PROCESSING, 'Processing'),
        (PROCESSED, 'Processed'),
        (CANCELLED, 'Cancelled'),
    ]

    etag = models.TextField('etag')
    filename = models.TextField('filename')
    data_file_kind = models.CharField('Data file kind', max_length=7, choices=DATA_FILE_KIND_CHOICES)
    county_num = models.IntegerField(null=True)
    created = models.DateTimeField()
    file_status = models.SmallIntegerField('file status', default=UNPROCESSED, choices=STATUS_CHOICES)

    @property
    def short_filename(self):
        "Use the filename portion of the path to show a friendly name in the admin."
        return os.path.split(self.filename)[-1]


class BadLineRange(models.Model):
    """
    Represents a consecutive set of bad lines from the same input file, with
    the same message, and either all warnings or all errors.
    """
    filename = models.CharField(max_length=255)
    first_line_no = models.IntegerField()
    last_line_no = models.IntegerField()
    example_line = models.TextField(help_text="First line from this range")
    message = models.TextField(db_index=True)
    is_warning = models.BooleanField(blank=True)

    class Meta:
        unique_together = (
            ('filename', 'first_line_no'),
        )


class BadLineTracker():
    """
    Instantiate one of these and use its methods to report bad lines.
    It'll spot runs of the same error on sequential lines and only
    create one BadLineRange object for each run.  Call flush() at
    end in case there's still one pending.

    Note: This doesn't bother to see if there's already a range in
    the database that we could add on to, so in rare cases it's possible
    we'll end up with range objects that could have been combined, but
    it doesn't seem worth the complexity of trying to avoid that.
    """
    def __init__(self, filename, model=BadLineRange):
        """
        We pass in model so we can use this from migrations easily.
        """
        self.filename = filename
        self.pending = None
        self.model = model

    def error(self, line_no, line, message):
        self.add(line_no, line, message, is_warning=False)

    def warning(self, line_no, line, message):
        self.add(line_no, line, message, is_warning=True)

    def add(self, line_no, line, message, is_warning):
        if '\x00' in line:
            line = repr(line)
        pending = self.pending
        if pending:
            # Can we use the one we've got going?
            if pending.message == message and pending.is_warning == is_warning and line_no == 1 + pending.last_line_no:
                # Yes, just extend this one
                pending.last_line_no += 1
                return
            # Can't use this one, save it and fall through to start a new one
            pending.save()
        # Start a new one
        self.pending = self.model(
            filename=self.filename,
            message=message,
            first_line_no=line_no,
            last_line_no=line_no,
            example_line=line,
            is_warning=is_warning,
        )

    def flush(self):
        """
        If we have an unsaved range, save it.
        """
        if self.pending:
            self.pending.save()
            self.pending = None


class ChangeTracker(models.Model):

    class Meta:
        verbose_name = "Change Tracker"
        verbose_name_plural = "Change Tracking"
        ordering = ('snapshot_dt', 'op_code')

    OP_CODE_ADD = 'A'
    OP_CODE_MODIFY = 'M'
    OP_CODE_CHOICES = [
        (OP_CODE_ADD, 'Add'),
        (OP_CODE_MODIFY, 'Modify'),
    ]
    op_code = models.CharField('Operation Code', max_length=1, choices=OP_CODE_CHOICES, db_index=True)
    model_name = models.CharField('Model Name', max_length=20, choices=FileTracker.DATA_FILE_KIND_CHOICES)
    md5_hash = models.CharField('MD5 Hash Value', max_length=32)
    data = JSONField(encoder=DjangoJSONEncoder)
    election_desc = models.CharField('election_desc', max_length=230, blank=True)
    file_tracker = models.ForeignKey('FileTracker', on_delete=models.CASCADE, related_name='changes')
    file_lineno = models.IntegerField(db_index=True)
    voter = models.ForeignKey('NCVoter', on_delete=models.CASCADE, related_name='changelog')
    snapshot_dt = models.DateTimeField()

    def get_prev(self):
        return self.voter.changelog.filter(snapshot_dt__lte=self.snapshot_dt).exclude(id=self.id).last()

    def build_version(self):
        data = {}
        changes = self.voter.changelog.filter(snapshot_dt__lte=self.snapshot_dt)
        for change in changes:
            data.update(change.data)
        return data


class NCVHis(models.Model):

    class Meta:
        verbose_name = "NC Voter History"
        verbose_name_plural = "NC Voter Histories"

    @staticmethod
    def parse_row(row):
        county_id = int(row['county_id'])
        row['county_id'] = county_id
        voted_county_id = int(row['voted_county_id'])
        row['voted_county_id'] = voted_county_id
        election_lbl_str = row['election_lbl']
        election_lbl_dt = datetime.strptime(election_lbl_str, '%m/%d/%Y')
        row['election_lbl'] = election_lbl_dt.date()
        return row

    @staticmethod
    def parse_existing(row):
        election_lbl_str = row.get('election_lbl')
        if election_lbl_str:
            election_lbl_dt = datetime.strptime(election_lbl_str, '%Y-%m-%d')
            row['election_lbl'] = election_lbl_dt.date()
        return row

    ncid = models.CharField('ncid', max_length=12, db_index=True)
    voter = models.ForeignKey('NCVoter', on_delete=models.CASCADE, related_name="histories", to_field='ncid', null=True)
    county_id = models.SmallIntegerField('county_id', db_index=True)
    county_desc = models.CharField('county_desc', max_length=60, blank=True)
    voter_reg_num = models.CharField('voter_reg_num', max_length=12, blank=True)
    election_lbl = models.DateField(max_length=10, blank=True)
    election_desc = models.CharField('election_desc', max_length=230, blank=True, db_index=True)
    voting_method = models.CharField('voting_method', max_length=32, blank=True)
    voted_party_cd = models.CharField('voted_party_cd', max_length=3, blank=True)
    voted_party_desc = models.CharField('voted_party_desc', max_length=60, blank=True)
    pct_label = models.CharField('pct_label', max_length=6, blank=True)
    pct_description = models.CharField('pct_description', max_length=60, blank=True)
    voted_county_id = models.SmallIntegerField('voted_county_id')
    voted_county_desc = models.CharField('voted_county_desc', max_length=60, blank=True)
    vtd_label = models.CharField('vtd_label', max_length=6, blank=True)
    vtd_description = models.CharField('vtd_description', max_length=60, blank=True)


class NCVoter(models.Model):
    ncid = models.TextField('ncid', unique=True, db_index=True)
    data = JSONField(
        null=True,
        default=None,
        encoder=DjangoJSONEncoder,
        help_text="Most recently known registration data for this voter, or NULL."
    )
    deleted = models.BooleanField(
        default=False,
        help_text="True if this voter not seen in most recent registration data."
    )

    class Meta:
        verbose_name = "NC Voter"
        verbose_name_plural = "NC Voters"
        indexes = [GinIndex(fields=['data'])]

    @staticmethod
    def parse_row(row):
        parsed_row = dict(row)
        county_id = row.get('county_id')
        if county_id:
            parsed_row['county_id'] = int(county_id)

        birth_age = row.get('birth_age')
        if birth_age:
            parsed_row['birth_age'] = int(birth_age)

        # Age should be an integer
        age = row.get('age')
        if age:
            parsed_row['age'] = int(age)

        drivers_lic_str = row.get('drivers_lic', '')
        parsed_row['drivers_lic'] = (drivers_lic_str.strip().upper() == 'Y')

        registr_dt_str = row.get('registr_dt')
        if registr_dt_str:
            registr_dt_str = registr_dt_str[:10]
            parsed_row['registr_dt'] = registr_dt_str

        confidential_ind_str = row.get('confidential_ind', '')
        parsed_row['confidential_ind'] = (confidential_ind_str.strip().upper() == "Y")

        raw_birth_year = row.get('birth_year')
        if raw_birth_year:
            parsed_row['birth_year'] = int(raw_birth_year)

        snapshot_dt = row.get('snapshot_dt')
        if snapshot_dt:
            snapshot_dt = snapshot_dt[:10]
            snapshot_dt = datetime.strptime(snapshot_dt, '%Y-%m-%d').replace(tzinfo=pytz.timezone('US/Eastern'))
            parsed_row['snapshot_dt'] = snapshot_dt

        city = row.get('res_city_desc')
        if city not in KNOWN_CITIES:
            logger.warning("City %s is not a known city. Either record is bad it needs to be added to KNOWN_CITIES.", city)
            # Add to known cities temporarily (during this execution) so that
            # we don't keep warning about it.
            KNOWN_CITIES.append(city)

        return parsed_row

    @classmethod
    def from_row(cls, parsed_row):
        return cls(ncid=parsed_row['ncid'], data=parsed_row)

    @classmethod
    def data_from_row(cls, row):
        if 'ncid' in row:
            row.pop('ncid')
        row['registr_dt'] = str(row['registr_dt'])
        return row, {}

    def build_version(self, index):
        changelog = self.changelog.all()
        data = {}
        nindex = len(changelog) - index
        for change in list(changelog)[:nindex]:
            data.update(change.data)
        return data

    def build_current(self):
        return self.build_version(0)

    def get_race_label(self):
        race_code = self.data.get('race_code', 'U')
        for code, label, description in RACE_FILTER_CHOICES:
            if code == race_code:
                return label

    def get_gender_label(self):
        gender_code = self.data.get('gender_code') or self.data.get('sex_code', 'U')
        for code, label, description in GENDER_FILTER_CHOICES:
            if code == gender_code:
                return label

    def get_party_label(self):
        party_code = self.data.get('party_cd', 'UNA')
        for code, label, description in PARTY_FILTER_CHOICES:
            if code == party_code:
                return label

    @classmethod
    def get_count(cls, filters):
        """
        Get the count from the cache table if possible, otherwise compute it from the materialized view.
        """
        cached_count_query = NCVoterQueryCache.objects.filter(qs_filters=filters).first()
        if cached_count_query:
            count = cached_count_query.count
        else:
            count = NCVoterQueryView.objects.filter(**filters).count()
            NCVoterQueryCache.objects.create(qs_filters=filters, count=count)
        return count

    @classmethod
    def get_random_sample(cls, filters, n):
        """
        Apply filters to NCVoter and return a random sample of N voter records (as a queryset).
        """
        count = cls.get_count(filters)
        query = NCVoterQueryView.objects.filter(**filters)
        if n >= count:
            # there are fewer than N records, so return them all
            voter_pks = query.values_list('pk', flat=True)
        else:
            # this 'randomness' assumes that records in NCVoterQueryView are not ordered in any
            # meaningful way
            offset = random.randint(0, count - n)
            voter_pks = query[offset:offset + n].values_list('pk', flat=True)
        return NCVoter.objects.filter(pk__in=voter_pks)


class NCVoterQueryView(models.Model):
    """
    This is an unmanaged model which maps to a materialized view. Our goal is to keep each row in
    this view as small as possible, with only the facets we need for search. All other voter data
    remains in the NCVoter.data JSON field, and we can join with it as needed.
    """
    party_cd = models.CharField('party code', max_length=3)
    county_id = models.IntegerField('county code')
    race_code = models.CharField('race code', max_length=1)
    ethnic_code = models.CharField('ethnicity code', max_length=2)
    status_cd = models.CharField('voter status code', max_length=1)
    birth_state = models.CharField('birth state', max_length=2, blank=True)
    gender_code = models.CharField('gender code', max_length=1)
    age = models.IntegerField(null=True)
    res_city_desc = models.CharField('city of residence', max_length=30, blank=True)
    zip_code = models.CharField('zip code', max_length=10, blank=True)

    class Meta:
        managed = False
        db_table = 'voter_ncvoterqueryview'

    @classmethod
    def refresh(cls):
        """
        Refresh the materialized view and refresh each of the cached query counts.
        """
        logger.info('Starting refresh of NCVoterQueryView')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY voter_ncvoterqueryview')
        logger.info('Refreshing %d NCVoterQueryCache counts', NCVoterQueryCache.objects.count())
        for cached_query in NCVoterQueryCache.objects.all():
            cached_query.count = NCVoterQueryView.objects.filter(**cached_query.qs_filters).count()
            cached_query.save(update_fields=['count'])
        logger.info('Done refreshing all NCVoterQueryCache counts')


class NCVoterQueryCache(models.Model):
    """
    Cache table of queryset filters and the resulting counts from applying those filters to the
    NCVoterQueryView model.

    We never invalidate these, so it is important that these be deleted (or better yet, refreshed)
    whenever new data is available in the NCVoter table. This is currently accomplished by calling
    NCVoterQueryView.refresh() after each import.
    """
    qs_filters = JSONField(
        encoder=DjangoJSONEncoder,
        help_text="Dictionary of queryset filters for NCVoterQueryView.",
        unique=True
    )
    count = models.IntegerField()
