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
			
			
def wiki_key(name='default'):	#Key for pages
	return db.Key.from_path('wiki', name)

class Page(db.Model):
	content = db.TextProperty()
	author = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)
	last_modified = db.DateTimeProperty(auto_now=True)

	@staticmethod
	def parent_key(path):
		return db.Key.from_path("/root" + path, "pages")

	@classmethod
	def by_id(cls, page_id, path):
		return cls.get_by_id(page_id, cls.parent_key(path))

	@classmethod
	def by_path(cls, path):
		query = cls.all()
		query.ancestor(cls.parent_key(path))
		query.order("-created")
		return query

	@classmethod
	def version_control(cls, version, path):
		"""
		Takes the current version number
		Then finds it in the database to return to a variable called page
		"""
		page = None

		if version:
			if version.isdigit():
				page = cls.by_id(int(version), path)

			if not page:
				return self.notfound()
		else:
			page = cls.by_path(path).get()

		return page

	def render(self): #Creates space for content 
		self._render_text = self.content.replace('\n', '<br>')
		return render_str("post.html", p=self)

