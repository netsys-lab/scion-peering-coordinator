"""Django settings for development with the postgres backend.
"""

import os
import redis
from .devel_common import *


ALLOWED_HOSTS = ['localhost', '192.168.244.2']


################
### Database ###
################

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'NAME': os.environ.get('POSTGRES_DB', 'postgres'),
        'USER': os.environ.get('POSTGRES_USER', 'peering_coord'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'peering_coord')
    }
}

######################
### Huey Task Queue ##
######################

HUEY = {
    'huey_class': 'huey.RedisHuey',
    'name': 'peering-coord',
    'immediate': False,
    'connection': {
        'connection_pool': redis.ConnectionPool(
            host='redis',
            port=6379
        )
    },
    'consumer': {
        'workers': 2
    }
}
