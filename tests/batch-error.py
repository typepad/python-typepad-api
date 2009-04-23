
from typepad import client, PromiseObject
import batchhttp.client

batchhttp.client.BATCH_ENDPOINT = 'http://api.typepad.com.tpapi-tp.dev.sixapart.com/batch-processor'

class Tiny(PromiseObject):
    pass

client.batch_request()
t = Tiny.get('http://api.typepad.com.tpapi-tp.dev.sixapart.com/groups/1.json')
client.batch(t)

# This should raise an HTTPException if the fault is reproduced
# ("httplib.HTTPException: Response was not a MIME multipart response set")
try:
    client.complete_batch()
except Tiny.NotFound:
    pass

assert t._delivered
