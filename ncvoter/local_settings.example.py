from .settings import *

DATABASES['default'].update({
    'PORT': 5455,
    'NAME': 'ncvotes',
    'USER': '',
    'PASSWORD': '',
})