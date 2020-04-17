import os
import re
import psycopg2
import psycopg2.extras
import functools
import urllib3
import certifi
import json
import secrets
from . import (
    config, md_utilities
)
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app as app
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.urls import url_parse

from MobiDetailsApp.db import get_db, close_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

# https://flask.palletsprojects.com/en/1.1.x/tutorial/views/
# -------------------------------------------------------------------


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        # username = urllib.parse.unquote(request.form['username'])
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
        elif not re.search(r'^[a-zA-Z0-9\._%\+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            error = 'The email address does not look valid.'
        else:
            http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
            # try:
            # read api key for mailboxvalidator
            apikey = config.mdconfig(section='email_check')['apikey']
            mv_url = 'https://api.mailboxvalidator.com/v1/validation/single?key={0}&format=json&email={1}'.format(apikey, email)
            try:
                mv_json = json.loads(http.request('GET', mv_url).data.decode('utf-8'))
            except Exception:
                mv_json = None
            if mv_json is not None:
                try:
                    if mv_json['credits_available'] > 0:
                        if mv_json['status'] == "False":
                            if mv_json['is_high_risk'] == "True" or mv_json['is_suppressed'] == "True" or mv_json['is_catchall'] == "True":
                                error = 'The email address is reported as risky or suppressed. \
                                        If this is not the case, please send us an email directly to \
                                        &#109;&#111;&#098;&#105;&#100;&#101;&#116;&#097;&#105;&#108;&#115;\
                                        &#046;&#105;&#117;&#114;&#099;&#064;&#103;&#109;&#097;&#105;&#108;&#046;&#099;&#111;&#109;.'
                            # else:valid adressese such as d-baux@chu-montpellier.fr are reported as False
                    else:
                        md_utilities.send_error_email(
                            md_utilities.prepare_email_html(
                                'MobiDetails email validation error',
                                '<p>mailboxvalidator credits == 0</p>'
                            ),
                            '[MobiDetails - Email Validation Error]'
                        )
                except Exception as e:
                    md_utilities.send_error_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails email validation error',
                            '<p>mailboxvalidator validation failed:<br/> {0} <br /> - from {1} with args: {2}</p>'.format(
                                mv_json,
                                os.path.basename(__file__),
                                e.args
                            )
                        ),
                        '[MobiDetails - Email Validation Error]'
                    )
            # 2nd check https://www.stopforumspam.com/
            # ex https://www.stopforumspam.com/api?ip=&email=&username=&f=json
            sfs_url = 'https://www.stopforumspam.com/api?ip={0}&email={1}&username={2}&f=json'.format(request.remote_addr, email, username)
            print(sfs_url)
            try:
                sfs_json = json.loads(http.request('GET', sfs_url).data.decode('utf-8'))
            except Exception:
                sfs_json = None
            if sfs_json is not None:
                try:
                    print(sfs_json)
                    if sfs_json['success'] == 1:
                        # sfs return a boolean for username, ip, email
                        # if email or ip = 1 => rejected
                        # username won't be rejected but a warning will be sent
                        if sfs_json['ip']['appears'] == 1 or \
                                sfs_json['email']['appears'] == 1:
                            error = 'Sorry, your input data is reported as risky. \
                                        If this is not the case, please send us an email directly to \
                                        &#109;&#111;&#098;&#105;&#100;&#101;&#116;&#097;&#105;&#108;&#115;&#046;&#105;&#117;&#114;&#099;&#064;&#103;&#109;&#097;&#105;&#108;&#046;&#099;&#111;&#109;.'
                        elif sfs_json['username']['appears'] == 1:
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails stop forum spam username validation error',
                                    '<p>Stop forum spam username validation failed (user created but to follow): \
                                    <br/> {0} <br /> - from {1} with url: {2}</p>'.format(
                                        sfs_json,
                                        os.path.basename(__file__),
                                        sfs_url
                                    )
                                ),
                                '[MobiDetails - Email Validation Error]'
                            )
                    else:
                        md_utilities.send_error_email(
                            md_utilities.prepare_email_html(
                                'MobiDetails stop forum spam validation error',
                                '<p>Stop forum spam validation failed:<br/> {0} <br /> - from {1} with url: {2}</p>'.format(
                                    sfs_json,
                                    os.path.basename(__file__),
                                    sfs_url
                                )
                            ),
                            '[MobiDetails - Email Validation Error]'
                        )
                except Exception as e:
                    md_utilities.send_error_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails stop forum spam validation error',
                            '<p>Stop forum spam validation failed:<br/> {0} <br /> - from {1} with args: {2}</p>'.format(
                                sfs_json,
                                os.path.basename(__file__),
                                e.args
                            )
                        ),
                        '[MobiDetails - Email Validation Error]'
                    )
        if error is None:
            curs.execute(
                "SELECT id FROM mobiuser WHERE username = '{0}' OR email = '{1}'".format(username, email)
            )
            if curs.fetchone() is not None:
                error = 'User {0} or email address {1} is already registered.'.format(username, email)

        if error is None:
            key = secrets.token_urlsafe(32)
            curs.execute(
                "INSERT INTO mobiuser (username, password, country, institute, email, api_key) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}')"
                .format(username, generate_password_hash(password), country, institute, email, key)
            )
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)
        if error is not None and not app.config['TESTING']:
            message_body = '<p>{0}</p><p>Originated from :</p><ul><li>Remote IP: {1}</li><li>Username: {2}</li>\
                           <li>Country: {3}</li><li>Institute: {4}</li><li>Email: {5}</li></ul>'.format(
                error, request.remote_addr, username, country, institute, email
            )
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    message_body
                ),
                '[MobiDetails - Registering Error]'
            )
        return render_template('auth/register.html', prev_username=username, prev_institute=institute, prev_email=email)

    return render_template('auth/register.html')

# -------------------------------------------------------------------
# login


@bp.route('/login', methods=('GET', 'POST'))
def login():
    #print(request.method)
    referrer_page = None
    if request.method == 'GET':
        # print(request.referrer)
        if request.referrer is not None and \
                url_parse(request.referrer).host == url_parse(request.base_url).host:
            # if url_parse(request.referrer).host == '10.34.20.79' or \
            #         url_parse(request.referrer).host == 'mobidetails.iurc.montp.inserm.fr':
            referrer_page = request.referrer
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            referrer_page = request.form['referrer_page']
        except Exception:
            pass
        # print(referrer_page)
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
            flash('You have successfully been logged in as {}.'.format(user["username"]))
            session['user_id'] = user['id']
            if referrer_page is None or \
                    (url_parse(referrer_page).host != url_parse(request.base_url).host or
                        re.search(r'(login|register)', referrer_page)):
                # not coming from mobidetails
                return redirect(url_for('auth.profile', mobiuser_id=0))
            else:
                return redirect(referrer_page)

        flash(error)

    return render_template('auth/login.html', referrer_page=referrer_page)

# -------------------------------------------------------------------
# for views that require login


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

# -------------------------------------------------------------------
# profile


@bp.route('/profile/<int:mobiuser_id>', methods=['GET', 'POST'])
@login_required
def profile(mobiuser_id=0):
    if re.search(r'^\d+$', str(mobiuser_id)):
        user_id = g.user['id']
        if mobiuser_id != 0:
            user_id = mobiuser_id
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT id, username, email, institute, country, api_key, email_pref FROM mobiuser  WHERE id = '{}'".format(user_id)
        )
        mobiuser = curs.fetchone()
        error = None
        if mobiuser is None:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    '<p>Bad profile attempt username: from id: {0} file: {1}</p>'.format(
                        g.user['id'],
                        os.path.basename(__file__)
                    )
                ),
                '[MobiDetails - Profile Error]'
            )
            error = 'You seem to be unknown by MobiDetails.'
            if mobiuser_id != 0:
                error = 'This user seems to be unknown by MobiDetails.'
        if mobiuser_id == 0:
            curs.execute(
                "SELECT id, c_name, gene_name, p_name, creation_date FROM variant_feature WHERE\
                creation_user = '{}' ORDER BY creation_date DESC".format(g.user['id'])
            )
            variants = curs.fetchall()
            num_var = curs.rowcount
    
            curs.execute(
                "SELECT a.id, a.c_name, a.ng_name, a.gene_name, a.p_name FROM variant_feature a, mobiuser_favourite b \
                WHERE  a.id = b.feature_id AND b.mobiuser_id = '{}' ORDER BY a.gene_name, a.ng_name".format(g.user['id'])
            )
            variants_favourite = curs.fetchall()
            if error is None:
                num_var_fav = curs.rowcount
                return render_template('auth/profile.html', mobiuser=mobiuser, view='own', num_var=num_var,
                                       num_var_fav=num_var_fav, variants=variants, variants_favourite=variants_favourite)
        elif error is None:
            # other profile view
            return render_template('auth/profile.html', mobiuser=mobiuser, view='other', num_var=None, num_var_fav=None, variants=None, variants_favourite=None)
    
        flash(error)
        return render_template('md/index.html')
    else:
        flash('Invalid user ID!!')
        return render_template('md/index.html')

# -------------------------------------------------------------------
# load profile when browsing


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

# -------------------------------------------------------------------
# logout


@bp.route('/logout')
def logout():
    session.clear()
    flash('You have successfully been logged out.')
    if request.referrer is not None and \
            url_parse(request.referrer).host == url_parse(request.base_url).host:
        return redirect(request.referrer)
    else:
        return redirect(url_for('index'))
