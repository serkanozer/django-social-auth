from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import SimpleCookie, HttpRequest
from django.test.client import Client, RequestFactory
import json
from django.utils.importlib import import_module
from mock import patch
from social_auth.views import complete

class DumbResponse(object):
    """
    Response from a call to, urllib2.urlopen()
    """
    
    def __init__(self, data_str, url=None):
        self.data_str = data_str
        self.url = url

    def read(self):
        return self.data_str


class NoBackendError(Exception):
    """
    Used when a client attempts to login with a invalid backend.
    """
    pass


class SocialClient(Client):
    """
    Test client to login/register a user
    Does so by mocking api posts/responses.

    Only supports facebook.
    """

    backends = ['facebook',]

    @patch('social_auth.utils.urlopen')
    def login(self, user, mock_urlopen, backend='facebook'):
        """
        Login or Register a facebook user.
        
        If the user has never logged in then they get registered and logged in.
        If the user has already registered, then they are logged in. 

        user: dict
        backend: 'facebook'

        example user:
        {
            'first_name': 'Django', 
            'last_name': 'Reinhardt', 
            'verified': True, 
            'name': 'Django Reinhardt', 
            'locale': 'en_US', 
            'hometown': {
                'id': '12345678', 
                'name': 'Any Town, Any State'
            }, 
            'expires': '4812', 
            'updated_time': '2012-01-29T19:27:32+0000', 
            'access_token': 'dummyToken', 
            'link': 'http://www.facebook.com/profile.php?id=1234', 
            'location': {
                'id': '108659242498155', 
                'name': 'Chicago, Illinois'
            }, 
            'gender': 'male', 
            'timezone': -6, 
            'id': '1234',
            'email': 'user@domain.com'
        }
        """


        if backend not in self.backends:
            raise NoBackendError("%s is not supported" % backend)

        access_token = "access_token=dummyToken&expires=4817"

        """
        mock out urlopen to get 
            1. access token
            2. user profile.
        """
        mock_urlopen.side_effect = [
            DumbResponse(access_token),
            DumbResponse(json.dumps(user))
        ]

        factory = RequestFactory()
        request = factory.post('', {'code': 'dummy','redirect_state': 'dummy'})

        engine = import_module(settings.SESSION_ENGINE)
        if self.session:
            request.session = self.session
        else:
            request.session = engine.SessionStore()

        request.user = AnonymousUser()
        request.session['facebook_state'] = 'dummy'

        # make it happen.
        redirect = complete(request, backend)

        request.session.save()
   
        # Set the cookie for this session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.cookies[session_cookie] = request.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        self.cookies[session_cookie].update(cookie_data)
    
        return True
