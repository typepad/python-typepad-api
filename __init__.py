from typepad.dataobject import DataObject
from typepad import fields
from typepad.remote import RemoteObject
from typepad.asset import *

class Client(object):
    """Provide some endpoints that aren't really models."""
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def get_user(self, http=None):
        """Returns the User as whom the client is authenticating."""
        if http is None:
            http = httplib2.Http()
        http.add_credentials(self.email, self.password)

        return User.get(urljoin(BASE_URL, '/accounts/@self.json'), http=http)
