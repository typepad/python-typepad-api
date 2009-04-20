"""

typepad provides connectivity to the TypePad API through remote objects.

"""

__version__ = '1.0'
__date__ = '20 April 2009'
__author__ = 'Six Apart, Ltd.'
__credits__ = """Brad Choate
Leah Culver
Mark Paschal"""

from remoteobjects import RemoteObject, ListObject
import batchhttp.client

from typepad.oauthclient import *

client = batchhttp.client.BatchClient(http=OAuthHttp())

from typepad.tpobject import *
from typepad import fields
from typepad.asset import *
