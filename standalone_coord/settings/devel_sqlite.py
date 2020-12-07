"""Django settings for development with the sqlite backend.
"""

from .devel_common import *


ALLOWED_HOSTS = ['192.168.244.2']


################
### Database ###
################

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3'
    }
}

######################
### Huey Task Queue ##
######################

HUEY = {
    'huey_class': 'huey.MemoryHuey',
    'name': 'peering-coord',
    'immediate': True,
    'consumer': {
        'workers': 2
    }
}
