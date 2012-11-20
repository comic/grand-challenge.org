import pdb
from dropbox import client, rest, session
from dropbox.session import DropboxSession
from dropbox.client import DropboxClient
from dropbox.rest import ErrorResponse

class DropboxDataProvider():
    """
    read and write files in a dropbox location
    """

    def __init__(self, app_key, app_secret, access_type, access_token, access_token_secret,
                  location='',):
        session = DropboxSession(app_key, app_secret, access_type)        
        session.set_token(access_token, access_token_secret)
        self.client = DropboxClient(session)
        self.account_info = self.client.account_info()
        self.location = location
        self.base_url = 'http://dl.dropbox.com/u/{uid}/'.format(**self.account_info)


    def read(self, filename):
        return self.client.get_file(filename).read()
