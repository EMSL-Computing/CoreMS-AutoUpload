from api import db


class User(db.Model):
    '''dummy user object for session reload'''

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    # encripted jwt token
    auth_token = db.Column(db.String)
