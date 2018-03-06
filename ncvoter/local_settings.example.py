from .settings import *

DATABASES['default'].update({
    'PORT': 5455,
    'NAME': 'ncvotes',
    'USER': '',
    'PASSWORD': '',
})

NCVOTER_DOWNLOAD_PATH = "/Volumes/Untitled/downloads/ncvoter"
NCVHIS_DOWNLOAD_PATH = "/Volumes/Untitled/downloads/ncvhis"