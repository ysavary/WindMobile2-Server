import binascii
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from pymongo import ASCENDING
from pymongo import MongoClient, uri_parser


class Oauth2Callback(TemplateView):
    template_name = "oauth2_callback.html"

    def authenticate(self):
        pass

    def save_user(self, username, email, user_info):
        # Save user in Django
        try:
            user = User.objects.get(username=username)
            user.email = email
        except User.DoesNotExist:
            user = User(username=username, email=email)
        user.save()

        # Save user_info
        mongo_db.users.update_one({'_id': username}, {'$set': {'user-info': user_info}}, upsert=True)

        # Generate One Time Token for API authentication
        mongo_db.login_ott.create_index([('createdAt', ASCENDING)], expireAfterSeconds=30)
        ott = binascii.hexlify(os.urandom(20)).decode('ascii')
        mongo_db.login_ott.insert_one({'_id': ott, 'username': username, 'createdAt': datetime.utcnow()})

        return ott


uri = uri_parser.parse_uri(settings.MONGODB_URL)
mongo_client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = mongo_client[uri['database']]
