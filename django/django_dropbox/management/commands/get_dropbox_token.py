from django.core.management.base import NoArgsCommand
from dropbox import rest, session
from django_dropbox.settings import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TYPE

class Command(NoArgsCommand):

    def handle_noargs(self, *args, **options):
        sess = session.DropboxSession(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TYPE)
        request_token = sess.obtain_request_token()

        url = sess.build_authorize_url(request_token)
        print "Url:", url
        print "Please visit this website and press the 'Allow' button, then hit 'Enter' here."
        raw_input()
        
        # This will fail if the user didn't visit the above URL and hit 'Allow'
        access_token = sess.obtain_access_token(request_token)

        print "DROPBOX_ACCESS_TOKEN = '%s'" % access_token.key
        print "DROPBOX_ACCESS_TOKEN_SECRET = '%s'" % access_token.secret