#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import re
import sys

import validator	#Module containing authentication functions
import logging

import webapp2
import jinja2

from models import User
from datetime import datetime, timedelta
from google.appengine.api import memcache
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), 
								autoescape=True)


DEBUG = bool(os.environ['SERVER_SOFTWARE'].startswith('Development'))
if DEBUG:
	logging.getLogger().setLevel(logging.DEBUG)

def render_str(template, **params):		
	t = jinja_env.get_template(template)	#Jinja template handler
	return t.render(params)


class Handler(webapp2.RequestHandler):
	"""
	Super handler for web app
	"""
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)	#Shorter version of self.response.out.write

	def render_str(self, template, **params):
		params['user'] = self.user 	#Store for valid user in everypage.
		return render_str(template, **params)

	def render(self, template, **kw):
		"""
		Takes a html template with variables
		and views them.
		"""
		self.write(self.render_str(template, **kw))

	def set_secure_cookie(self, name, val):
		cookie_val = validator.make_secure_val(val)
		self.response.headers.add_header(
			'Set-Cookie',
			'%s=%s; Path=/' % (name, cookie_val))

	def read_secure_cookie(self, name):
		cookie_val = self.request.cookies.get(name)
		return cookie_val and validator.check_secure_val(cookie_val)

	def login(self, user):
		self.set_secure_cookie('user_id', str(user.key().id()))

	def logout(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

	def initialize(self, *a, **kw):	
		"""
		Checks if user id and username is valid
		As well as format to JSON for API
		"""
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')
		self.user = uid and User.by_id(int(uid))

		if self.request.url.endswith(".json"):
			self.format = "json"
		else:
			self.format = "html"


		def notfound(self):
			self.error(404)
			self.write('<h1>404: Oopsy</h1> Sorry, my friend page does not exist')




class Signup(Handler):
	def get(self):
		next_url = self.request.headers.get('referer', '/')
		self.render("signup-form.html", next_url=next_url)

	def post(self):
		have_error = False

		self.next_url = str(self.request.get('next_url'))
		if not self.next_url or self.next_url.startswith('/login'):
			self.next_url = '/'

		self.username = self.request.get('username')
		self.password = self.request.get('password')
		self.verify = self.request.get('verify')
		self.email = self.request.get('email')

		params = dict(username=self.username,	#Input variables to a dictionary
						email=self.email)

		"""
		Below is for validating user registration
		If any validation is false it will render an
		error to user registration
		"""
		if not validator.valid_username(self.username):	
			params['error_username'] = "Invalid username"
			have_error = True

		if not validator.valid_password(self.password):
			params['error_password'] = "Invalid password"
			have_error = True

		elif self.password != self.verify:
			params['error_verify'] = "Does not match password"
			have_error = True

		if not validator.valid_email(self.email):
			params['error_email'] = "Invalid email"

		if have_error:
			self.render('signup-form.html', **params)
		else:
			self.done()	#Refer to done() at Register class below

	def done(self, *a, **kw):
		raise NotImplementedError


class Register(Signup):
	def done(self):
		"""
		Check if user does not exist
		If not, create new user and login new user
		"""
		user = User.by_name(self.username)
		if user:
			msg = 'That user already exists.'
			self.render('signup-form.html', error_username=msg)
		else:		
			user = User.register(self.username, self.password, self.email)
			user.put()

			self.login(user)

			self.redirect('/')


class Login(Handler):
	def get(self):
		self.render('login.html')

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')

		user = User.login(username, password)

		if user:
			self.login(user)
			self.redirect('/')
		else:	#Return error and login page if false
			msg = "Please check your inputs"
			self.render("login.html", error=msg)


class Logout(Handler):
	def get(self):
		next_url = self.request.headers.get('referer', '/')
		self.logout()
		self.redirect("/login")




class HistoryPage(Handler):
	"""
	Gets the most recent version of a page,
	Turns it into a list
	Allows user to review old versions
	"""
	def get(self, path):
		query = Page.by_path(path)
		query.fetch(limit=100)

		posts = list(query)	#Transform the query into a list
		if posts:
			self.render("history.html", path=path, posts=posts)
		else:
			self.redirect("/edit" + path)


class EditPage(Handler):
	def get(self, path):
		if not self.user:
			self.redirect("/login")

		version = self.request.get("v")
		page = Page.version_control(version, path)

		self.render("newpost.html", path=path, page=page)

	def post(self, path):
		"""
		Show the most recent version for editing
		If there is none, create newpost.
		Both must be edited, then put it into the database
		"""
		if not self.user:
			self.error(400)
			return

		content = self.request.get("content")
		old_page = Page.by_path(path).get()
		author = self.user.name

		if not(old_page or content):
			error = "Please enter some new content!"
			self.render("newpost.html", error)
			return
		elif not old_page or old_page.content != content:	
			page = Page(parent=Page.parent_key(path), content=content, author=author)
			page.put()

		self.redirect(path) #Show the new edited version


class WikiPage(Handler):
	"""
	Show the requested version of a page
	if not edit the current version
	"""
	def get(self, path):
		version = self.request.get("v")
		page = Page.version_control(version, path)

		if page:
			self.render("permalink.html", page=page, path=path)
		else:
			self.redirect("/_edit" + path)


PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
app = webapp2.WSGIApplication([('/signup', Register),
								('/login', Login),
								('/logout', Logout),
								('/_history' + PAGE_RE, HistoryPage),
								('/_edit' + PAGE_RE, EditPage),
								(PAGE_RE, WikiPage),
								], debug=DEBUG)
