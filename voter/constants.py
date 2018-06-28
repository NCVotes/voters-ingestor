from ncvoter.known_cities import KNOWN_CITIES

# Code, Label, Description
STATUS_FILTER_CHOICES = [
    ('A', 'Active', "are actively registered"),
    ('D', 'Denied', "were denied registration"),
    ('I', 'Inactive', "have inactive registrations"),
    ('R', 'Removed', "have had their registration removed"),
    ('S', 'Temporary', 'have temporary registrations'),
]

GENDER_FILTER_CHOICES = [
    ('F', 'Female', "are <em>female</em>"),
    ('M', 'Male', "are <em>male</em>"),
    ('U', 'Undesignated', "are <em>undesignated</em>"),
]

PARTY_FILTER_CHOICES = [
    ('DEM', 'Democrat', 'are <em>Democrats</em>'),
    ('GRE', 'Green', 'are <em>Greens</em>'),
    ('LIB', 'Libertarian', 'are <em>Libertarian</em>'),
    ('REP', 'Republican', 'are <em>Republicans</em>'),
    ('UNA', 'Unaffiliated', 'are <em>Unaffiliated</em>'),
]

COUNTIES = [
    "ALAMANCE",
    "ALEXANDER",
    "ALLEGHANY",
    "ANSON",
    "ASHE",
    "AVERY",
    "BEAUFORT",
    "BERTIE",
    "BLADEN",
    "BRUNSWICK",
    "BUNCOMBE",
    "BURKE",
    "CABARRUS",
    "CALDWELL",
    "CAMDEN",
    "CARTERET",
    "CASWELL",
    "CATAWBA",
    "CHATHAM",
    "CHEROKEE",
    "CHOWAN",
    "CLAY",
    "CLEVELAND",
    "COLUMBUS",
    "CRAVEN",
    "CUMBERLAND",
    "CURRITUCK",
    "DARE",
    "DAVIDSON",
    "DAVIE",
    "DUPLIN",
    "DURHAM",
    "EDGECOMBE",
    "FORSYTH",
    "FRANKLIN",
    "GASTON",
    "GATES",
    "GRAHAM",
    "GRANVILLE",
    "GREENE",
    "GUILFORD",
    "HALIFAX",
    "HARNETT",
    "HAYWOOD",
    "HENDERSON",
    "HERTFORD",
    "HOKE",
    "HYDE",
    "IREDELL",
    "JACKSON",
    "JOHNSTON",
    "JONES",
    "LEE",
    "LENOIR",
    "LINCOLN",
    "MCDOWELL",
    "MACON",
    "MADISON",
    "MARTIN",
    "MECKLENBURG",
    "MITCHELL",
    "MONTGOMERY",
    "MOORE",
    "NASH",
    "NEW HANOVER",
    "NORTHAMPTON",
    "ONSLOW",
    "ORANGE",
    "PAMLICO",
    "PASQUOTANK",
    "PENDER",
    "PERQUIMANS",
    "PERSON",
    "PITT",
    "POLK",
    "RANDOLPH",
    "RICHMOND",
    "ROBESON",
    "ROCKINGHAM",
    "ROWAN",
    "RUTHERFORD",
    "SAMPSON",
    "SCOTLAND",
    "STANLY",
    "STOKES",
    "SURRY",
    "SWAIN",
    "TRANSYLVANIA",
    "TYRRELL",
    "UNION",
    "VANCE",
    "WAKE",
    "WARREN",
    "WASHINGTON",
    "WATAUGA",
    "WAYNE",
    "WILKES",
    "WILSON",
    "YADKIN",
    "YANCEY",
]

COUNTY_FILTER_CHOICES = [
    (str(i), county.title(), "live in <em>%s</em> county" % county.title())
    for i, county in enumerate(COUNTIES, start=1)
]

CITY_FILTER_CHOICES = [
    (city, city.title(), "live in <em>%s</em>" % city.title())
    for city in KNOWN_CITIES
]

RACE_FILTER_CHOICES = [
    ('A', 'Asian', 'Asian'),
    ('B', 'Black', 'Black or African American'),
    # 'H' is not a race_code in the NCVoter data, but we populate our materialized
    # view with that value if the ethnic_code of a voter is HL (Hispanic/Latino)
    ('H', 'Hispanic', 'Hispanic/Latino'),
    ('M', 'Multi-racial', 'Two or More Races'),
    ('I', 'Native', 'Indian American or Alaska Native'),
    ('O', 'Other', 'Other'),
    ('U', 'Undesignated', 'Undesignated'),
    ('W', 'White', 'White'),
]

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

STATE_FILTER_CHOICES = [
    (abb, name, "were born in <em>%s</em>" % name)
    for abb, name in STATE_ABBREVS
]
