#import functools
import re
import psycopg2
import psycopg2.extras
import functools
import urllib3
import certifi
import json
from . import config
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from MobiDetailsApp.db import get_db, close_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

#https://flask.palletsprojects.com/en/1.1.x/tutorial/views/
######################################################################
@bp.route('/register', methods=('GET', 'POST'))
def register():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		country = request.form['country']
		institute = request.form['institute']
		email = request.form['email']
	
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		error = None
	
		if not username:
			error = 'Username is required.'
		elif len(username) < 5:
			error = 'Username should be at least 5 characters.'
		elif not password:
			error = 'Password is required.'
		elif len(password) < 8 or not re.match('[a-zA-Z0-9]+', password):
			error = 'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'
		elif not country or re.match('--', country):
			error = 'Country is required.'
		elif not institute:
			error = 'Institute is required.'
		elif not email:
			error = 'Email is required.'
		elif not re.match('^[a-zA-Z0-9\._%\+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
			error = 'The email address does not look valid.'			
		else:
			http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
			#try:
			# read api key for mailboxvalidator
			apikey = config.email_check_key()
			mv_url = 'https://api.mailboxvalidator.com/v1/validation/single?key={0}&format=json&email={1}'.format(apikey, email)
			try:
				mv_json = json.loads(http.request('GET', mv_url).data.decode('utf-8'))
			except:
				mv_json = None
			if mv_json is not None:
				try:
					if mv_json['credits_available'] > 0:
						if mv_json['status'] == "False":
							if mv_json['is_high_risk'] == "True" or mv_json['is_suppressed'] == "True" or mv_json['is_catchall'] == "True":
								error = 'The email address is reported as risky or suppressed. If this is not the case, please send us an email directly at &#100;&#097;&#118;&#105;&#100;&#046;&#098;&#097;&#117;&#120;&#064;&#105;&#110;&#115;&#101;&#114;&#109;&#046;&#102;&#114;.'
							#else:valid adressese such as d-baux@chu-montpellier.fr are reported as False
							#	error ='The email address does not look genuine. If this is not the case, please send us an email directly at &#100;&#097;&#118;&#105;&#100;&#046;&#098;&#097;&#117;&#120;&#064;&#105;&#110;&#115;&#101;&#114;&#109;&#046;&#102;&#114;.'
				except:
					pass
		if error is None:
			curs.execute(
				"SELECT id FROM mobiuser WHERE username = '{0}' OR email = '{1}'".format(username, email)
			)
			if curs.fetchone() is not None:
				error = 'User {0} or email address {1} is already registered.'.format(username, email)

		if error is None:
			curs.execute(
				"INSERT INTO mobiuser (username, password, country, institute, email) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}')".format(username, generate_password_hash(password), country, institute, email)
			)
			db.commit()
			return redirect(url_for('auth.login'))

		flash(error)

	return render_template('auth/register.html')

######################################################################
#login
@bp.route('/login', methods=('GET', 'POST'))
def login():
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		error = None
		curs.execute(
			"SELECT * FROM mobiuser WHERE email = '{}'".format(email)
		)
		user = curs.fetchone()
		if user is None:
			error = 'Unknown email.'
		elif not check_password_hash(user['password'], password):
			error = 'Incorrect password.'

		if error is None:
			session.clear()
			session['user_id'] = user['id']
			return redirect(url_for('index'))

		flash(error)

	return render_template('auth/login.html')

######################################################################
#for views that require login
def login_required(view):
	@functools.wraps(view)
	def wrapped_view(**kwargs):
		if g.user is None:
			return redirect(url_for('auth.login'))

		return view(**kwargs)

	return wrapped_view

######################################################################
#profile
@bp.route('/profile')
@login_required
def profile():
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT username, email, institute, country FROM mobiuser  WHERE id = '{}'".format(g.user['id'])
	)
	mobiuser = curs.fetchone()
	error = None
	num_var = 0
	num_var_fav = 0
	if mobiuser is None:
		error = 'You seem to be unknown by MobiDetails.'	
	
	curs.execute(
		"SELECT id, c_name, gene_name, p_name, creation_date FROM variant_feature WHERE creation_user = '{}' ORDER BY creation_date DESC".format(g.user['id'])
	)
	variants = curs.fetchall()
	#if error is None:
	num_var = len(variants)
		#return render_template('auth/profile.html', mobiuser=mobiuser, variants=variants, num_var=num_var)
	
	curs.execute(
		"SELECT a.id, a.c_name, a.ng_name, a.gene_name, a.p_name FROM variant_feature a, mobiuser_favourite b WHERE  a.id = b.feature_id AND b.mobiuser_id = '{}' ORDER BY a.gene_name, a.ng_name".format(g.user['id'])
	)
	variants_favourite = curs.fetchall()
	if error is None:
		num_var_fav = len(variants_favourite)
		return render_template('auth/profile.html', mobiuser=mobiuser, num_var=num_var, num_var_fav=num_var_fav, variants=variants, variants_favourite=variants_favourite)
	
	flash(error)
	return render_template('auth/index.html')

######################################################################
#load profile when browsing
@bp.before_app_request
def load_logged_in_user():
	user_id = session.get('user_id')

	if user_id is None:
		g.user = None
	else:
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		curs.execute(
			"SELECT * FROM mobiuser WHERE id = '{}'".format(user_id,)
		)
		g.user = curs.fetchone()
	close_db()

######################################################################
#logout
@bp.route('/logout')
def logout():
	session.clear()
	return redirect(url_for('index'))



