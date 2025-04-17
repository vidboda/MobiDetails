from flask import url_for
import pytest
from datetime import datetime
# from flask import g, session
# python 3.9 style
# from .test_ajax import get_db
# python 3.6 style
from test_ajax import get_db
from test_api import get_generic_api_key


def test_register(client, app):
    with app.app_context():
        # test register returns no error
        assert client.get(url_for('auth.register')).status_code == 200
        response = client.post(
            # '/auth/register', data={
            url_for('auth.register'), data={
                'username': 'davidbaux', 'password': 'a',
                'country': 'a', 'institute': 'a', 'email': 'david.baux@inserm.fr',
                'acad': 'academic'
            }
        )
        assert response.status_code == 200

        # test db returns a value
        db_pool, db = get_db()
        curs = db.cursor()
        curs.execute(
            "SELECT * FROM mobiuser WHERE username = 'davidbaux'",
        )
        res = curs.fetchone()
        db_pool.putconn(db)
        assert res is not None

# multiple tests to check known username and email returns a message


@pytest.mark.parametrize(('username', 'password', 'institute', 'email', 'country', 'message'), (
    ('djsdlm', 'ss9kghgF', 'IURC ,;.-()', 'david.baux@inserm.fr', 'Albania', b'is already registered.'),
    ('david', 'ss9kghgF', 'IURC ,;.-()', 'kevin@inserm.fr', 'Albania', b'is already registered.'),
    ('1', 's', 'IURC ,;.-()', 'v', 'Albania', b'Username should be at least 5 characters'),
    ('djsdlm', 's', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'sfafg', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'SFAGF', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', '15467854566', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'SFAGF125FAR87', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'sfagf12587sadefz', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'sF12,z', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'ss9kghgF', 'IURC ,;.-()', 'kevin@inserm.f', 'Albania', b'The email address does not look valid.'),
    # below test should trigger stopforumsspam but on mddev w/ pytest the app can not connect, while the regular dev app does (!?)
    # ('alinar', 'ss9kghgF', 'IURC ,;.-()', 'testing@xrumer.ru', 'Albania', b'Sorry, your input data is reported as risky.'),
    ('djsdlm', 'ss9kghgF', 'IURC ,;.-()', 'kevin@inserm.fr', 'a', b'Unrecognized country.'),
    ('djsdlm', 'ss9kghgF', 'IURC *', 'kevin@inserm.fr', 'Albania', b'Invalid characters in the Institute field (please use letters, numbers and ,;.-()).'),
))
def test_register_validate_input(client, app, username, institute, password, email, country, message):
    with app.app_context():
        response = client.post(
            url_for('auth.register'),
            data={
                'username': username, 'password': password, 'country': country,
                'institute': institute, 'email': email, 'acad': 'academic'
            }
        )
        print(response.get_data())
        print(url_for('auth.register'))
        assert message in response.get_data()

# multiple tests check cannot login with bad credentials


@pytest.mark.parametrize(('email', 'password', 'message'), (
    ('1', 's', b'Unknown email.'),
    ('david.baux@inserm.fr', 'r', b'Incorrect password.'),
))
def test_login_validate_input(client, app, email, password, message):
    with app.app_context():
        response = client.post(
            url_for('auth.login'),
            data={'email': email, 'password': password}
        )
        print(response.get_data())
        assert message in response.get_data()

# test activation
api_key = get_generic_api_key()


@pytest.mark.parametrize(('mobiuser_id', 'api_key', 'message'), (
    (2, api_key, b'User id does not exist.'),
    (4, api_key, b'Your account is already activated, you may now log in using your email address.')
))
def test_activate(client, app, mobiuser_id, api_key, message):
    with app.app_context():
        response = client.get(
            url_for('auth.activate', mobiuser_id=mobiuser_id, api_key=api_key)
        )
        print(response.get_data())
        assert message in response.get_data()

# test profile page


@pytest.mark.parametrize(('mobiuser_id', 'message'), (
    (0, b'API key'),
    (9999,  b'unknown'),
    (10,  b'Username'),
))
def test_profile(client, app, auth, mobiuser_id, message):
    with app.app_context():
        assert client.get(url_for('auth.profile', mobiuser_id=mobiuser_id)).status_code == 302
        response = client.get(url_for('auth.profile', mobiuser_id=mobiuser_id), follow_redirects=True)
        assert b'check_login_form' in response.get_data()  # means we are in the login page

# test log out redirect to homepage


def test_logout(client, app):
    with app.app_context():
        response = client.get(url_for('auth.logout'))
        print(response.headers['Location'])
        assert 'http://mddev.pmmg.priv:5001/' == response.headers['Location']
        # assert b'Homepage' in response.get_data()

# test forgot my password form


@pytest.mark.parametrize(('mobiuser_email', 'message'), (
    ('david.bauxinserm.fr', b'The email address does not look valid.'),
    ('david@insermfr', b'The email address does not look valid.'),
    ('david@inserm.fr', b'seems to be unknown by the system.'),
    ('david.baux@inserm.fr', b'Please check your e-mail inbox'),
))
def test_forgot_pass(client, app, mobiuser_email, message):
    with app.app_context():
        response = client.post(
            url_for('auth.forgot_pass'),
            data={'email': mobiuser_email}
        )
        print(response.get_data())
        assert message in response.get_data()

# test reset password


@pytest.mark.parametrize(('mobiuser_id', 'api_key', 'timestamp', 'message'), (
    (2, api_key, None, b'API key and user id do not seem to fit.'),
    ('test', api_key, None, b'Some parameters are not legal'),
    (4, api_key, None, b'Please fill in the form to reset your password with a new one.'),
    (4, api_key, '593612854.360794', b'This link is outdated.'),
    (4, api_key, '2593612854.360794', b'This link is outdated.'),
))
def test_reset_password(client, app, mobiuser_id, api_key, timestamp, message):
    if timestamp is None:
        timestamp = datetime.timestamp(datetime.now())
    with app.app_context():
        response = client.get(
            '{0}?mobiuser_id={1}&api_key={2}&ts={3}'.format(
                url_for('auth.reset_password'),
                mobiuser_id,
                api_key,
                timestamp
            )
        )
        print(response.get_data())
        assert message in response.get_data()

# test variant list


@pytest.mark.parametrize(('list_name', 'http_code'), (
    ('USH2A_RP_LGM_2021', 200),
    ('test', 404),
))
def test_variant_list(client, app, list_name, http_code):
    with app.app_context():
        assert client.get(
            url_for('auth.variant_list', list_name=list_name),
        ).status_code == http_code
