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
    configuration, md_utilities
)
from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, session, url_for, current_app as app
)
from werkzeug.security import check_password_hash, generate_password_hash
# from werkzeug.urls import url_parse
from datetime import datetime
from IPy import IP, IPSet
from MobiDetailsApp.db import get_db, close_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

# https://flask.palletsprojects.com/en/1.1.x/tutorial/views/
# -------------------------------------------------------------------


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    if request.method == 'POST':
        error = username = password = country = institute = email = None
        if not request.form['username']:
            error = 'Username is required.'
        else:
            match_obj = re.search(r'^([\w-]{5,100})$', request.form['username'])
            if match_obj:
                username = match_obj.group(1)
            else:
                error = """
                Username should be at least 5 characters and contain only letters and numbers.
                """
        if not request.form['password']:
            error = 'Password is required.'
        elif not error:
            # https://stackoverflow.com/questions/4429847/check-if-string-contains-both-number-and-letter-at-least
            match_obj = re.search(r'(?!^[0-9]*$)(?!^[a-z]*$)(?!^[A-Z]*$)(?!^[a-zA-Z]*$)(?!^[a-z0-9]*$)(?!^[A-Z0-9]*$)^(.{8,})$', request.form['password'])
            if match_obj:
                password = match_obj.group(1)
            else:
                error = """
            Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.
            """
        if not request.form['country'] or \
                re.match('--', request.form['country']):
            error = 'Country is required.'
        elif not error:
            if request.form['country'] in md_utilities.countries:
                # match_obj = re.search(r'^([^-][^-].+)')
                # if match_obj:
                country = md_utilities.countries[md_utilities.countries.index(request.form['country'])]
            else:
                error = 'Unrecognized country.'
        if not request.form['institute']:
            error = 'Institute is required.'
        elif not error:
            match_obj = re.search(r'^([\w\(\),;\.\s-]+)$', request.form['institute'])
            if match_obj:
                institute = match_obj.group(1)
            else:
                error = 'Invalid characters in the Institute field (please use letters, numbers and ,;.-()).'
        if not request.form['email']:
            error = 'Email is required.'
        elif not error:
            match_obj = re.search(
                r'^([a-zA-Z0-9\._%\+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$',
                request.form['email']
            )
            if match_obj:
                email = match_obj.group(1)
            else:
                error = 'The email address does not look valid.'
        academic_val = 't' if request.form['acad'] == 'academic' else 'f'
        header = md_utilities.api_agent
        if not request.remote_addr:
            error = 'Invalid request'
        elif not error:
            match_obj = re.search(r'^([\d\.]+)$', request.remote_addr)
            if match_obj:
                remote_ip = match_obj.group(1)
            else:
                error = 'Invalid char in IP address.'
       
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        if not error:
            curs.execute(
                """
                SELECT id
                FROM mobiuser
                WHERE username = %s OR email = %s
                """,
                (username, email)
            )
            if curs.fetchone() is not None:
                error = 'User {0} or email address {1}\
                 is already registered.'.format(
                    username, email
                )
        if not error:
            http = urllib3.PoolManager(
                cert_reqs='CERT_REQUIRED',
                ca_certs=certifi.where()
            )
            # try:
            # read api key for mailboxvalidator
            apikey = configuration.mdconfig(section='email_check')['apikey']
            mv_url = 'https://api.mailboxvalidator.com/v1/validation/single?key={0}&format=json&email={1}'.format(
                apikey, email
            )
            try:
                mv_json = json.loads(
                    http.request(
                        'GET',
                        mv_url,
                        headers=header
                    ).data.decode('utf-8')
                )
            except Exception:
                mv_json = None
            if mv_json:
                try:
                    if mv_json['credits_available'] > 0:
                        if mv_json['status'] == "False":
                            if (mv_json['is_high_risk'] == "True" or
                                    mv_json['is_suppressed'] == "True" or
                                    mv_json['is_catchall'] == "True"):
                                error = """
                                The email address is reported as risky or suppressed.
                                If this is not the case, please send
                                us an email directly to
                                &#109;&#111;&#098;&#105;&#100;&#101;&#116;&#097;&#105;&#108;&#115;&#064;&#099;&#104;&#117;&#045;&#109;&#111;&#110;&#116;&#112;&#101;&#108;&#108;&#105;&#101;&#114;&#046;&#102;&#114;.
                                """
                            # else:valid adresses such as
                            # d-baux@chu-montpellier.fr are reported as False
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
                            """
                            <p>mailboxvalidator validation failed: <br/> {0} <br /> - from {1} with args: {2}</p>
                            """.format(
                                mv_json,
                                os.path.basename(__file__),
                                e.args
                            )
                        ),
                        '[MobiDetails - Email Validation Error]'
                    )
            # 2nd check https://www.stopforumspam.com/
            # ex https://stopforumspam.com/api?ip=&email=&username=&f=json
            sfs_url = 'https://stopforumspam.com/api?ip={0}&email={1}&username={2}&f=json'.format(
                remote_ip,
                email,
                username
            )
            # print(sfs_url)
            try:
                sfs_json = json.loads(
                    http.request(
                        'GET',
                        sfs_url,
                        headers=header
                    ).data.decode('utf-8')
                )
            except Exception as e:
                sfs_json = None
            if sfs_json:
                try:
                    # print(sfs_json)
                    if sfs_json['success'] == 1:
                        # sfs return a boolean for username, ip, email
                        # if email or ip = 1 => rejected
                        # username won't be rejected but a warning will be sent
                        # build IP white list
                        # https://pypi.org/project/IPy/
                        ip_list = re.split(',', app.config['IP_WHITE_LIST'])
                        ip_white_list = IPSet([IP(ip_list.pop(0))])
                        for ip in ip_list:
                            ip_white_list.add(IP(ip))
                        is_in_white_list = any([remote_ip in white_net for white_net in ip_white_list])
                        # print(ip_white_list)
                        # print(is_in_white_list)
                        if (sfs_json['ip']['appears'] == 1 and \
                                is_in_white_list is False) or \
                                sfs_json['email']['appears'] == 1:
                        # if sfs_json['ip']['appears'] == 1 or \
                        #         sfs_json['email']['appears'] == 1:
                            error = """
                            Sorry, your input data is reported as risky.
                            If this is not the case, please send
                            us an email directly to
                            &#109;&#111;&#098;&#105;&#100;&#101;&#116;&#097;&#105;&#108;&#115;&#064;&#099;&#104;&#117;&#045;&#109;&#111;&#110;&#116;&#112;&#101;&#108;&#108;&#105;&#101;&#114;&#046;&#102;&#114;.
                            """
                        elif sfs_json['username']['appears'] == 1:
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails stop forum spam \
                                    username validation error',
                                    """
                                    <p>Stop forum spam username validation failed (user created but to follow):
                                    <br/> {0} <br /> - from {1} with url: {2}</p>
                                    """.format(
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
                                """
                                <p>Stop forum spam validation failed:<br/> {0}<br /> - from {1} with url: {2}</p>
                                """.format(
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
                            """
                            <p>Stop forum spam validation failed:<br/> {0}<br /> - from {1} with args: {2}</p>
                            """.format(
                                sfs_json,
                                os.path.basename(__file__),
                                e.args
                            )
                        ),
                        '[MobiDetails - Email Validation Error]'
                    )
        if not error:
            key = secrets.token_urlsafe(32)
            curs.execute(
                """
                INSERT INTO mobiuser (username, password, country, institute, email, api_key, academic, activated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'f')
                RETURNING id
                """,
                (username,
                 generate_password_hash(password),
                 country,
                 institute,
                 email,
                 key,
                 academic_val)
            )
            user_id = curs.fetchone()[0]
            db.commit()
            md_utilities.send_email(
                md_utilities.prepare_email_html(
                    'MobiDetails - Account activation',
                    """
                    Dear {0},
                    <p>thank you for registering in MobiDetails.
                     We hope you will find this website useful.</p>
                    <p>Please follow the link below to activate
                     your MobiDetails account:</p>
                    <p><a href="{1}{2}" title="Activate your MD account">
                    Activate your MD account</a></p>
                    <p>If you do not know why you received this email,
                    do not follow the link and please alert
                    {3}.</p><br />
                    """.format(
                        username,
                        request.host_url.rstrip('/'),
                        url_for(
                            'auth.activate',
                            mobiuser_id=user_id,
                            api_key=key
                        ),
                        app.config["MAIL_USERNAME"]
                    ),
                    False
                ),
                '[MobiDetails - Account activation]',
                [email],
                [app.config["MAIL_ERROR_RECIPIENT"]]
            )
            flash(
                """
                <br /><p>Your account has been created but requires an activation step.
                An email has been sent to {} with an activation link.</p><br />
                """.format(email),
                'w3-pale-green'
            )
            close_db()
            return redirect(url_for('md.index'), code=302)

        flash(error, 'w3-pale-red')
        if error and \
                not app.config['TESTING']:
            message_body = """
            <p>{0}</p><p>Originated from :</p><ul><li>
            Remote IP: {1}</li><li>Username: {2}</li>
            <li>Country: {3}</li><li>Institute: {4}</li>
            <li>Email: {5}</li></ul>
            """.format(
                error, request.remote_addr, username, country, institute, email
            )
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    message_body
                ),
                '[MobiDetails - Registering Error]'
            )
        close_db()
        return render_template(
            'auth/register.html',
            countries=md_utilities.countries,
            prev_username=username,
            prev_institute=institute,
            prev_email=email
        )

    return render_template(
        'auth/register.html',
        countries=md_utilities.countries
    )

# -------------------------------------------------------------------
# login


@bp.route('/login', methods=('GET', 'POST'))
def login():
    referrer_page = None
    if request.method == 'GET':
        referrer_page = request.referrer
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            referrer_page = request.form['referrer_page']
        except Exception:
            # if no referrer page, pass
            pass
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        error = None
        curs.execute(
            """
            SELECT *
            FROM mobiuser
            WHERE email = %s
            """,
            (email,)
        )
        user = curs.fetchone()
        if user is None:
            error = 'Unknown email.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'
        elif user['activated'] is False:
            error = """
            This account is not activated.
            An email to activate your account
            has been sent to {}
            """.format(user['email'])
            # message, mail_object, receiver
            md_utilities.send_email(
                md_utilities.prepare_email_html(
                    'MobiDetails - Account activation',
                    """
                    Dear {0},
                    <p>please follow the link below to activate your MobiDetails account:</p>
                    <p><a href="{1}{2}" title="Activate your MD account">
                    Activate your MD account</a></p>
                    <p>If you do not know why you receive this email,
                    do not follow the link and please alert
                    {3}.</p><br />
                    """.format(
                        user['username'],
                        request.host_url.rstrip('/'),
                        url_for(
                            'auth.activate',
                            mobiuser_id=user['id'],
                            api_key=user['api_key']
                        ),
                        app.config["MAIL_USERNAME"]
                    ),
                    False
                ),
                '[MobiDetails - Account activation]',
                [email]
            )

        if error is None:
            session.clear()
            close_db()
            flash(
                'You have successfully been logged in as {}.'.format(
                    user["username"]), 'w3-pale-green'
                )
            session['user_id'] = user['id']
            # if referrer_page is None or \
            #         (url_parse(referrer_page).host !=
            #             url_parse(request.base_url).host or
            #             re.search(r'(login|register)', referrer_page)):
            if referrer_page is None or \
                    (md_utilities.parse_url(referrer_page).hostname !=
                        md_utilities.parse_url(request.base_url).hostname or
                        re.search(r'(login|register)', referrer_page)):
                return redirect(
                    url_for(
                        'auth.profile',
                        run_mode=md_utilities.get_running_mode(),
                        mobiuser_id=0
                    ),
                    code=302
                )
            else:
                # if referrer_page is not None and \
                #         (url_parse(referrer_page).host ==
                #             url_parse(request.base_url).host):
                if referrer_page is not None and \
                        (md_utilities.parse_url(referrer_page).hostname ==
                            md_utilities.parse_url(request.base_url).hostname):
                    # not coming from mobidetails
                    # rebuild redirect URL
                    return redirect(
                        md_utilities.build_redirect_url(
                            referrer_page
                        ),
                        code=302
                    )
                else:
                    return redirect(
                        url_for(
                            'auth.profile',
                            run_mode=md_utilities.get_running_mode(),
                            mobiuser_id=0
                        ),
                        code=302
                    )
        close_db()
        flash(error, 'w3-pale-red')
    # not coming from mobidetails
    # rebuild redirect URL
    return render_template(
        'auth/login.html',
        run_mode=md_utilities.get_running_mode(),
        referrer_page=md_utilities.build_redirect_url(
            referrer_page
        )
    )

# -------------------------------------------------------------------
# profile activation


@bp.route('/activate/<int:mobiuser_id>/<string:api_key>', methods=['GET'])
def activate(mobiuser_id, api_key):
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    if isinstance(mobiuser_id, int) and \
            isinstance(api_key, str):
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT id, api_key, activated
            FROM mobiuser
            WHERE id = %s
            """,
            (mobiuser_id,)
        )
        user = curs.fetchone()
        if user is None:
            message_body = """
            <p>Account activation exception</p><p>Recived API key: {0} and mobiuser_id: {1} from {2}
            """.format(
                    api_key, mobiuser_id, request.remote_addr
                )
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    message_body
                ),
                '[MobiDetails - Activation Error]'
            )
            flash(
                'User id does not exist. An admin has been warned.',
                'w3-pale-red'
            )
            close_db()
            return render_template('md/index.html')
        else:
            if user['activated'] is False and \
                    user['api_key'] == api_key and \
                    user['id'] == mobiuser_id:
                new_api_key = secrets.token_urlsafe(32)
                curs.execute(
                    "UPDATE mobiuser SET activated = 't', api_key = %s WHERE \
                    id = %s AND api_key = %s",
                    (new_api_key, user['id'], user['api_key'])
                )
                db.commit()
                flash(
                    'Your account has been activated, you may now log in using your email address.',
                    'w3-pale-green'
                )
                close_db()
                return render_template('auth/login.html')
            if user['activated'] is True and \
                    user['id'] == mobiuser_id:
                flash(
                    'Your account is already activated, you may now log in using your email address.',
                    'w3-pale-green'
                )
                return render_template('auth/login.html')
    return render_template('md/unknown.html')

# -------------------------------------------------------------------
# for views that require login


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'), code=302)
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
            """
            SELECT *
            FROM mobiuser
            WHERE id = %s
            """,
            (user_id,)
        )
        mobiuser = curs.fetchone()
        error = None
        if mobiuser is None:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    '<p>Bad profile attempt username: from id: {0} file: {1}\
</p>'.format(
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
                """
                SELECT a.id, a.c_name, a.gene_symbol, a.refseq,
                    a.p_name, a.creation_date, b.mobiuser_id, b.type
                FROM variant_feature a
                LEFT JOIN mobiuser_favourite b ON a.id = b.feature_id
                WHERE a.creation_user = %s
                ORDER BY a.creation_date DESC
                """,
                (g.user['id'],)
            )
            variants = curs.fetchall()
            num_var = curs.rowcount

            curs.execute(
                """
                SELECT * FROM variants_groups
                WHERE mobiuser_id = %s
                ORDER BY creation_date DESC
                """,
                (g.user['id'],)
            )
            variant_groups = curs.fetchall()
            variant_groups_number = curs.rowcount
            # we need to modify the username to propose a list name without special characters
            clean_username = re.sub(r'[^\w]', '_', mobiuser['username'])

            curs.execute(
                """
                SELECT a.id, a.c_name, a.ng_name, a.gene_symbol,
                    a.refseq, a.p_name, b.type
                FROM variant_feature a
                LEFT JOIN mobiuser_favourite b ON a.id = b.feature_id
                WHERE b.mobiuser_id = %s
                ORDER BY a.gene_symbol, a.ng_name
                """,
                (g.user['id'],)
            )
            variants_favourite = curs.fetchall()

            # count favourites
            curs.execute(
                """
                SELECT mobiuser_id
                FROM mobiuser_favourite
                WHERE mobiuser_id = %s
                    AND type IN (1, 3)
                """,
                (g.user['id'],)
            )
            num_var_fav = curs.rowcount

            # count clinvar watched
            curs.execute(
                """
                SELECT mobiuser_id
                FROM mobiuser_favourite
                WHERE mobiuser_id = %s
                    AND type IN (2, 3)
                """,
                (g.user['id'],)
            )
            num_var_clinv = curs.rowcount

            if error is None:
                # num_var_fav = curs.rowcount
                close_db()
                return render_template(
                    'auth/profile.html',
                    run_mode=md_utilities.get_running_mode(),
                    mobiuser=mobiuser,
                    view='own',
                    num_var=num_var,
                    num_var_fav=num_var_fav,
                    num_var_clinv=num_var_clinv,
                    variants=variants,
                    variants_favourite=variants_favourite,
                    variant_groups=variant_groups,
                    variant_groups_number=variant_groups_number + 1,
                    clean_username=clean_username
                )
        elif error is None:
            # other profile view
            close_db()
            return render_template(
                'auth/profile.html',
                run_mode=md_utilities.get_running_mode(),
                mobiuser=mobiuser,
                view='other',
                num_var=None,
                num_var_fav=None,
                variants=None,
                variants_favourite=None,
                variant_groups=None,
                variant_groups_number=None,
                clean_username=None
            )

        flash(error, 'w3-pale-red')
        close_db()
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    else:
        ('Invalid user ID!!', 'w3-pale-red')
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )

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
            "SELECT * FROM mobiuser WHERE id = %s",
            (user_id,)
        )
        g.user = curs.fetchone()
        close_db()

# -------------------------------------------------------------------
# logout


@bp.route('/logout')
def logout():
    session.clear()
    flash('You have successfully been logged out.', 'w3-pale-green')
    # https://pythonise.com/series/learning-flask/the-flask-request-object
    # url attributes
    # scheme auth username password raw_username raw_password
    # ascii_host host port path query fragment
    if request.referrer is not None and \
            (md_utilities.parse_url(request.referrer).hostname == md_utilities.host['dev'] or
                md_utilities.parse_url(request.referrer).hostname == md_utilities.host['prod']):
        redirect_url = md_utilities.build_redirect_url(request.referrer)
        print(redirect_url)
        return redirect(redirect_url, code=302)
    else:
        return redirect(url_for('index'), code=302)

# -------------------------------------------------------------------
# forgot password


@bp.route('/forgot_pass', methods=['GET', 'POST'])
def forgot_pass():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    if request.method == 'GET':
        return render_template('auth/forgot_pass.html')
    elif request.method == 'POST':
        error = None
        email = request.form['email']
        if not re.search(
                r'^[a-zA-Z0-9\._%\+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                email
                ):
            error = 'The email address does not look valid.'
            flash(error, 'w3-pale-red')
            return render_template('auth/forgot_pass.html')
        else:
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                "SELECT * FROM mobiuser WHERE email = %s",
                (email,)
            )
            user = curs.fetchone()
            if user is None:
                close_db()
                error = """
                Your email address {} seems to be unknown by the system.
                """.format(email)
                flash(error, 'w3-pale-red')
                return render_template('auth/forgot_pass.html')
            # message, mail_object, receiver
            md_utilities.send_email(
                md_utilities.prepare_email_html(
                    'MobiDetails - Reset your password',
                    """
                    Dear {0},
                    <p>please follow the link below to reset your MobiDetails password:</p>
                    <p><a href="{1}{2}" title="Reset your MD password">
                    Reset your MD password</a></p>
                    <p>If you do not know why you receive this email,
                    do not follow the link and please alert
                    {3}.</p><br />
                    """.format(
                        user['username'],
                        request.host_url.rstrip('/'),
                        url_for(
                            'auth.reset_password',
                            mobiuser_id=user['id'],
                            api_key=user['api_key'],
                            ts=datetime.timestamp(datetime.now())
                        ),
                        app.config["MAIL_USERNAME"]
                    ),
                    False
                ),
                '[MobiDetails - Password reset]',
                [email]
            )
            flash(
                """
                Please check your e-mail inbox.
                You should have received a message with a link
                to reset your password
                """
                , 'w3-pale-green'
            )
            close_db()
            return render_template('auth/forgot_pass.html')
    return render_template('md/unknown.html')

# -------------------------------------------------------------------
# reset password


@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    if request.method == 'GET':
        if re.search(r'^\d+$', request.args.get('mobiuser_id')) and \
                re.search(r'^[\d\.]+$', request.args.get('ts')):
            mobiuser_id = request.args.get('mobiuser_id')
            api_key = request.args.get('api_key')
            original_timestamp = request.args.get('ts')
            # we will keep the link alive for 30 minutes i.e. 1800 s
            if float(float(datetime.timestamp(
                datetime.now())
                ) - float(original_timestamp)) > 1800 or \
               float(float(datetime.timestamp(
                datetime.now())
                    ) - float(original_timestamp)) < 0:
                flash(
                    """
                    This link is outdated. Please try again the procedure.
                    """
                    , 'w3-pale-red'
                )
                return render_template('auth/login.html')
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT id, api_key, activated
                FROM mobiuser
                WHERE id = %s AND api_key = %s
                """,
                (mobiuser_id, api_key)
            )
            user = curs.fetchone()
            if user is None:
                message_body = """
                <p>Password reset exception</p><p>Received API key: {0} and mobiuser_id: {1} from {2}
                """.format(
                            api_key, mobiuser_id, request.remote_addr
                        )
                md_utilities.send_error_email(
                    md_utilities.prepare_email_html(
                        'MobiDetails error',
                        message_body
                    ),
                    '[MobiDetails - Password reset Error]'
                )
                flash(
                    """
                    API key and user id do not seem to fit. An admin has been warned
                    """
                    , 'w3-pale-red'
                )
                close_db()
                return render_template('auth/forgot_pass.html')
            else:
                close_db()
                return render_template(
                    'auth/reset_pass.html',
                    mobiuser_id=mobiuser_id,
                    api_key=api_key
                )
        else:
            message_body = """
            <p>Password reset exception</p><p>Received timestamp: {0} and mobiuser_id: {1} from {2}
            """.format(
                    request.args.get('ts'),
                    request.args.get('mobiuser_id'),
                    request.remote_addr
                )
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    message_body
                ),
                '[MobiDetails - Password reset Error]'
            )
            flash(
                """
                Some parameters are not legal. An admin has been warned
                """
                , 'w3-pale-red'
            )
            return render_template('auth/forgot_pass.html')
    elif request.method == 'POST':
        mobiuser_id = request.form['mobiuser_id']
        api_key = request.form['api_key']
        password = request.form['password']
        error = None
        if len(password) < 8 or \
                not re.search(r'[a-z]', password) or \
                not re.search(r'[A-Z]', password) or \
                not re.search(r'[0-9]', password):
            error = """
                Password should be at least 8 characters and mix at least
                letters (upper and lower case) and numbers.
            """
        else:
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                UPDATE mobiuser SET password= %s
                WHERE id = %s AND api_key = %s
                """,
                (generate_password_hash(password), mobiuser_id, api_key)
            )
            db.commit()
            flash('Your password has just been reset.', 'w3-pale-green')
            close_db()
            return render_template('auth/login.html')
        if error is not None:
            flash(error, 'w3-pale-red')
            return render_template(
                'auth/reset_pass.html',
                mobiuser_id=mobiuser_id,
                api_key=api_key
            )
    return render_template('md/unknown.html')

# -------------------------------------------------------------------
# variant lists associated to a user


@bp.route('/variant_list/<string:list_name>', methods=['GET'])
def variant_list(list_name):
    if len(list_name) < 31 and \
            re.search(r'^[\w]+$', list_name):
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT a.variant_ids, b.username, a.creation_date, a.list_name
            FROM variants_groups a, mobiuser b
            WHERE a.mobiuser_id = b.id AND list_name = %s
            """,
            (list_name,)
        )
        res = curs.fetchone()
        # we've got an ARRAY of variants_ids and want to query on them...
        if res:
            res_ids_string = "("
            for id in res['variant_ids']:
                res_ids_string += "{}, ".format(id)
            res_ids_string = res_ids_string[:-2]
            res_ids_string += ")"
            # print(res_ids_string)
            curs.execute(
                """
                SELECT a.id, a.c_name, a.p_name, a.gene_symbol, a.refseq, a.creation_user, a.creation_date, b.username
                FROM variant_feature a, mobiuser b
                WHERE  a.creation_user = b.id AND a.id IN {0}
                """.format(res_ids_string)
            )
            variants = curs.fetchall()
            close_db()
            return render_template('md/variant_multiple.html', variants=variants, unique_url_info=res)
        else:
            close_db()
            return render_template('errors/404.html'), 404
    else:
        return render_template('errors/404.html'), 404
