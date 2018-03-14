from datetime import datetime
import pytz
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict


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
    STATUS_CHOICES = [(UNPROCESSED, 'Unprocessed'), (PROCESSING, 'Processing'), (PROCESSED, 'Processed')]

    etag = models.TextField('etag')
    filename = models.TextField('filename')
    data_file_kind = models.CharField('Data file kind', max_length=7, choices=DATA_FILE_KIND_CHOICES)
    county_num = models.IntegerField(null=True)
    created = models.DateTimeField()
    file_status = models.SmallIntegerField('file status', default=UNPROCESSED, choices=STATUS_CHOICES)
    change_tracker_processed = models.BooleanField(null=False, blank=True, default=False)


class BadLine(models.Model):
    filename = models.CharField(max_length=255)
    line_no = models.IntegerField()
    line = models.TextField()
    message = models.TextField()
    is_warning = models.BooleanField(blank=True)

    class Meta:
        unique_together = (
            ('filename', 'line_no'),
        )

    @classmethod
    def error(cls, filename, line_no, line, message):
        cls.objects.create(
            filename = filename,
            line_no = line_no,
            line = line,
            message = message,
            is_warning = False,
        )
    
    @classmethod
    def warning(cls, filename, line_no, line, message):
        cls.objects.create(
            filename = filename,
            line_no = line_no,
            line = line,
            message = message,
            is_warning = True,
        )


class ChangeTracker(models.Model):

    class Meta:
        verbose_name = "Change Tracker"
        verbose_name_plural = "Change Tracking"
        ordering = ('snapshot_dt',)

    OP_CODE_ADD = 'A'
    OP_CODE_MODIFY = 'M'
    OP_CODE_CHOICES = [
        (OP_CODE_ADD, 'Add'),
        (OP_CODE_MODIFY, 'Modify'),
    ]
    op_code = models.CharField('Operation Code', max_length=1, choices=OP_CODE_CHOICES)
    model_name = models.CharField('Model Name', max_length=20, choices=FileTracker.DATA_FILE_KIND_CHOICES)
    md5_hash = models.CharField('MD5 Hash Value', max_length=32)
    data = JSONField(encoder=DjangoJSONEncoder)
    election_desc = models.CharField('election_desc', max_length=230, blank=True)
    file_tracker = models.ForeignKey('FileTracker', on_delete=models.CASCADE, related_name='changes')
    file_lineno = models.IntegerField(blank=True, null=True)
    voter = models.ForeignKey('NCVoter', on_delete=models.CASCADE, related_name='changelog')
    snapshot_dt = models.DateTimeField()


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

        return row

    # Use build_current() instead now
    @staticmethod
    def parse_existing(row):
        existing_data = model_to_dict(row)
        del existing_data['id']
        existing_data = {k: v for k, v in existing_data.items() if (v is not None and v != '')}
        return existing_data

    @classmethod
    def from_row(cls, row):
        return cls(ncid=row['ncid'])

    @classmethod
    def data_from_row(cls, row):
        if 'ncid' in row:
            row.pop('ncid')
        row['registr_dt'] = str(row['registr_dt'])
        return row, {}

    def build_current(self):
        changelog = self.changelog.all()
        data = {}
        for change in changelog:
            data.update(change.data)
        return data

    ncid = models.TextField('ncid', unique=True, db_index=True)


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
