from ncvoter.settings import *  # noqa: F403

DATABASES['default'].update({  # noqa: F405
    'PORT': 5455,
    'NAME': 'ncvoter',
    'USER': '',
    'PASSWORD': '',
})

NCVOTER_DOWNLOAD_PATH = "/Volumes/Untitled/downloads/ncvoter"
NCVHIS_DOWNLOAD_PATH = "/Volumes/Untitled/downloads/ncvhis"
