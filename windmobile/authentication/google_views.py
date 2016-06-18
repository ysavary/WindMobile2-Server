import requests
from django.http import HttpResponseRedirect
from oauth2client import client
from rest_framework.reverse import reverse

from .views import Oauth2Callback


class GoogleOauth2Callback(Oauth2Callback):
    def get(self, request, *args, **kwargs):
        flow = client.flow_from_clientsecrets(
            'google_client_secret.json',
            scope=['profile', 'email'],
            redirect_uri=reverse('auth.google_oauth2callback', request=self.request))

        if 'code' not in self.request.GET:
            auth_uri = flow.step1_get_authorize_url()
            return HttpResponseRedirect(auth_uri)
        else:
            auth_code = self.request.GET['code']
            token = flow.step2_exchange(auth_code)
            user_info = requests.get('https://www.googleapis.com/oauth2/v3/userinfo',
                                     params={'access_token': token.access_token}).json()
            username = "google-{0}".format(user_info['sub'])
            email = user_info['email'] or ''

            ott = self.save_user(username, email, user_info)
            context = {
                'ott': ott,
                'redirect_url': '/stations/list'
            }
            return self.render_to_response(context)
