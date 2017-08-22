MONGODB_URL = 'mongodb://localhost:27017/windmobile'

WINDMOBILE_LOG_DIR = None

GOOGLE_API_KEY = ''

WINDLINE_URL = ''

CHECKWX_API_KEY = ''

SENTRY_URL = ''

try:
    from local_settings import *
except ImportError:
    pass
