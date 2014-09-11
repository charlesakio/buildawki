import validator 

from datetime import datetime, timedelta
from google.appengine.api import memcache
from google.appengine.ext import db

def users_key(group='default'):	#Create key for users
	return db.Key.from_path('users', group)

class User(db.Model):
	name = db.StringProperty(required=True)
	pw_hash = db.StringProperty(required=True)
	email = db.StringProperty()

	@classmethod
	def by_id(cls, uid):
		return User.get_by_id(uid, parent=users_key())	#Return user if it matches

	@classmethod
	def by_name(cls, name):
		user = cls.all().filter('name', name).get()	
		return user

	@classmethod
	def register(cls, name, pw, email=None):
		pw_hash = validator.make_pw_hash(name, pw)	#Create password hash
		return User(parent=users_key(), 
					name=name,
					pw_hash=pw_hash,
					email=email)

	@classmethod
	def login(cls, name, pw):
		user = cls.by_name(name)
		if user and validator.valid_pw(name, pw, user.pw_hash): #If input password is true return user
			return user
