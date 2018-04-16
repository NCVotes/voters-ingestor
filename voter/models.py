import os

from datetime import datetime
import pytz
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder


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

    class Meta:
        verbose_name = "NC Voter"
        verbose_name_plural = "NC Voters"
        # db_table = 'voter_ncvoter'

    @staticmethod
    def parse_row(row):
        parsed_row = dict(row)
        county_id = row.get('county_id')
        if county_id:
            parsed_row['county_id'] = int(county_id)

        birth_age = row.get('birth_age')
        if birth_age:
            parsed_row['birth_age'] = int(birth_age)

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


COUNTY_CODES = {
    1: 'ALAMANCE',
    2: 'ALEXANDER',
    3: 'ALLEGHANY',
    4: 'ANSON',
    5: 'ASHE',
    6: 'AVERY',
    7: 'BEAUFORT',
    8: 'BERTIE',
    9: 'BLADEN',
    10: 'BRUNSWICK',
    11: 'BUNCOMBE',
    12: 'BURKE',
    13: 'CABARRUS',
    14: 'CALDWELL',
    15: 'CAMDEN',
    16: 'CARTERET',
    17: 'CASWELL',
    18: 'CATAWBA',
    19: 'CHATHAM',
    20: 'CHEROKEE',
    21: 'CHOWAN',
    22: 'CLAY',
    23: 'CLEVELAND',
    24: 'COLUMBUS',
    25: 'CRAVEN',
    26: 'CUMBERLAND',
    27: 'CURRITUCK',
    28: 'DARE',
    29: 'DAVIDSON',
    30: 'DAVIE',
    31: 'DUPLIN',
    32: 'DURHAM',
    33: 'EDGECOMBE',
    34: 'FORSYTH',
    35: 'FRANKLIN',
    36: 'GASTON',
    37: 'GATES',
    38: 'GRAHAM',
    39: 'GRANVILLE',
    40: 'GREENE',
    41: 'GUILFORD',
    42: 'HALIFAX',
    43: 'HARNETT',
    44: 'HAYWOOD',
    45: 'HENDERSON',
    46: 'HERTFORD',
    47: 'HOKE',
    48: 'HYDE',
    49: 'IREDELL',
    50: 'JACKSON',
    51: 'JOHNSTON',
    52: 'JONES',
    53: 'LEE',
    54: 'LENOIR',
    55: 'LINCOLN',
    56: 'MACON',
    57: 'MADISON',
    58: 'MARTIN',
    59: 'MCDOWELL',
    60: 'MECKLENBURG',
    61: 'MITCHELL',
    62: 'MONTGOMERY',
    63: 'MOORE',
    64: 'NASH',
    65: 'NEWHANOVER',
    66: 'NORTHAMPTON',
    67: 'ONSLOW',
    68: 'ORANGE',
    69: 'PAMLICO',
    70: 'PASQUOTANK',
    71: 'PENDER',
    72: 'PERQUIMANS',
    73: 'PERSON',
    74: 'PITT',
    75: 'POLK',
    76: 'RANDOLPH',
    77: 'RICHMOND',
    78: 'ROBESON',
    79: 'ROCKINGHAM',
    80: 'ROWAN',
    81: 'RUTHERFORD',
    82: 'SAMPSON',
    83: 'SCOTLAND',
    84: 'STANLY',
    85: 'STOKES',
    86: 'SURRY',
    87: 'SWAIN',
    88: 'TRANSYLVANIA',
    89: 'TYRRELL',
    90: 'UNION',
    91: 'VANCE',
    92: 'WAKE',
    93: 'WARREN',
    94: 'WASHINGTON',
    95: 'WATAUGA',
    96: 'WAYNE',
    97: 'WILKES',
    98: 'WILSON',
    99: 'YADKIN',
    00: 'YANCEY',
}

RACE_CODES = {
    'B': 'BLACK or AFRICAN AMERICAN',
    'I': 'AMERICAN INDIAN or ALASKA NATIVE',
    'O': 'OTHER',
    'W': 'WHITE',
    'U': 'UNDESIGNATED',
    'A': 'ASIAN',
    'M': 'TWO or MORE RACES',
}

GENDER_CODES = {
    'M': 'M',
    'F': 'F',
}

STATE_ABBREVS = [
    ('AL', 'Alabama'),
    ('AK', 'Alaska'),
    ('AS', 'American Samoa'),
    ('AZ', 'Arizona'),
    ('AR', 'Arkansas'),
    ('CA', 'California'),
    ('CO', 'Colorado'),
    ('CT', 'Connecticut'),
    ('DE', 'Delaware'),
    ('DC', 'District of Columbia'),
    ('FM', 'Federated States of Micronesia'),
    ('FL', 'Florida'),
    ('GA', 'Georgia'),
    ('GU', 'Guam'),
    ('HI', 'Hawaii'),
    ('ID', 'Idaho'),
    ('IL', 'Illinois'),
    ('IN', 'Indiana'),
    ('IA', 'Iowa'),
    ('KS', 'Kansas'),
    ('KY', 'Kentucky'),
    ('LA', 'Louisiana'),
    ('ME', 'Maine'),
    ('MH', 'Marshall Islands'),
    ('MD', 'Maryland'),
    ('MA', 'Massachusetts'),
    ('MI', 'Michigan'),
    ('MN', 'Minnesota'),
    ('MS', 'Mississippi'),
    ('MO', 'Missouri'),
    ('MT', 'Montana'),
    ('NE', 'Nebraska'),
    ('NV', 'Nevada'),
    ('NH', 'New Hampshire'),
    ('NJ', 'New Jersey'),
    ('NM', 'New Mexico'),
    ('NY', 'New York'),
    ('NC', 'North Carolina'),
    ('ND', 'North Dakota'),
    ('MP', 'Northern Mariana Islands'),
    ('OH', 'Ohio'),
    ('OK', 'Oklahoma'),
    ('OR', 'Oregon'),
    ('PW', 'Palau'),
    ('PA', 'Pennsylvania'),
    ('PR', 'Puerto Rico'),
    ('RI', 'Rhode Island'),
    ('SC', 'South Carolina'),
    ('SD', 'South Dakota'),
    ('TN', 'Tennessee'),
    ('TX', 'Texas'),
    ('UT', 'Utah'),
    ('VT', 'Vermont'),
    ('VI', 'Virgin Islands'),
    ('VA', 'Virginia'),
    ('WA', 'Washington'),
    ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'),
    ('WY', 'Wyoming'),
]
