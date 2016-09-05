import boto3
from functools import wraps
from flask_digestauth import authdigest
from .. import model

authdigest.DigestAuthentication.addDigestHashAlg('sha256', hashlib.sha256)

# From http://flask.pocoo.org/snippets/31/
class FlaskRealmDigestDB(authdigest.RealmDigestDB):
    def requires_auth(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            request = flask.request
            if not self.isAuthenticated(request):
                return self.challenge()
            return f(*args, **kwargs)
        return decorated


class ApothecaryRealmDigestDB(FlaskRealmDigestDB):
    def __init__(self, realm, algorithm='sha256', dynamodb=boto3.resource('dynamodb')):
        self.dynamodb = dynamodb
        FlaskRealmDigestDB.__init__(self, realm, algorithm)

    def newDB(self):
        return DynamoDbDict(self.dynamodb)

    class DynamoDbDict(object):
        def __init__(self, dynamodb):
            self.dynamodb = dynamodb

        def get(self, user_id, default=None):
            user = User.get(self.dynamodb, user_id)
            return user.pw_hash

        def __contains__(self, user_id):
            from_dynamo = User.get(user_id)
            return 'Item' in from_dynamo

        def pop(self, user_id, default=None):
            User(user_id, '').delete()
            return user_id or default

        def __delitem__(self, user_id):
            User(user_id, '').delete()
