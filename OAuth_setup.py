from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from authentication import *

config = Config('.env')

oauth = OAuth(config)
oauth.register(
    name='google',
    client_id= config_credentials['GOOGLE_CLIENT_ID'],
    client_secret = config_credentials['GOOGLE_CLIENT_SECRET'],
    authorize_url = 'https://accounts.google.com/o/oauth2/auth',
    authorize_params = None,
    access_token_url = 'https://accounts.google.com/o/oauth2/token',
    access_token_params = None,
    refresh_token_url = None,
    client_kwargs={
        'scope': 'openid email profile'
    }

)
