import re
import hmac
import random
import hashlib

from string import letters

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")	#Regex for valid username
def valid_username(username):
	return username and USER_RE.match(username)	#Return username if it matches username regex


PASS_RE = re.compile(r"^.{3,20}$")	#Regex for valid password
def valid_password(password):
    return password and PASS_RE.match(password)	#Return password if it matches username regex 


EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')	#Regex for valid email
def valid_email(email):
    return not email or EMAIL_RE.match(email)	#Return email if it matches username regex 


secret = 'fart' # Secret value for hashing

def make_secure_val(val):
	""" 
	Take input called val
	Place it in function called hmac.new to hash
	Then use hexdigest to add further security
	Return val and hashed value
	"""
	return '%s|%s' % (val, hmac.new(secret, val). hexdigest())

def check_secure_val(secure_val):
	"""
	Split input called secure_val
	Return if its true
	"""
	val = secure_val.split('|')[0]
	if secure_val == make_secure_val(val):
		return val

def make_salt(length=5):
	return ''.join(random.choice(letters) for x in xrange(length))	#Return created salt

def make_pw_hash(name, pw, salt=None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name + pw + salt).hexdigest() #Create new hash
	return '%s|%s' % (salt, h)

def valid_pw(name, password, h):
	salt = h.split('|')[0]
	return h == make_pw_hash(name, password, salt) #Return True if h matches hash


