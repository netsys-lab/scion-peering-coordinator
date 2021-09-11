"""Django settings for development with the sqlite backend.
"""

from .devel_common import *


ALLOWED_HOSTS = ['localhost', '192.168.244.2']


################
### Database ###
################

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3'
    }
}
