import pytest
from datetime import datetime
# from flask import g, session
from test_ajax import get_db


def test_register(client, app):
    # test register returns no error
    assert client.get('/auth/register').status_code == 200
    response = client.post(
        '/auth/register', data={
            'username': 'davidbaux', 'password': 'a',
            'country': 'a', 'institute': 'a', 'email': 'david.baux@inserm.fr',
            'acad': 'academic'
        }
    )
    assert response.status_code == 200

    # test db returns a value
    with app.app_context():
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
    ('davidbaux', 'ss9kghgF', 'IURC ,;.-()', 'kevin@inserm.fr', 'Albania', b'is already registered.'),
    ('1', 's', 'IURC ,;.-()', 'v', 'Albania', b'Username should be at least 5 characters'),
    ('djsdlm', 's', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'sfafg', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'SFAGF', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', '15467854566', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'SFAGF125FAR87', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'sfagf12587sadefz', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'sF12,z', 'IURC ,;.-()', 'v', 'Albania', b'Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.'),
    ('djsdlm', 'ss9kghgF', 'IURC ,;.-()', 'kevin@inserm.f', 'Albania', b'The email address does not look valid.'),
    ('alinar', 'ss9kghgF', 'IURC ,;.-()', 'testing@xrumer.ru', 'Albania', b'Sorry, your input data is reported as risky.'),
    ('djsdlm', 'ss9kghgF', 'IURC ,;.-()', 'kevin@inserm.fr', 'a', b'Unrecognized country.'),
    ('djsdlm', 'ss9kghgF', 'IURC *', 'kevin@inserm.fr', 'Albania', b'Invalid characters in the Institute field (please use letters, numbers and ,;.-()).'),
))
def test_register_validate_input(client, username, institute, password, email, country, message):
    response = client.post(
        '/auth/register',
        data={
            'username': username, 'password': password, 'country': country,
            'institute': institute, 'email': email, 'acad': 'academic'
        }
    )
    print(response.get_data())
    assert message in response.get_data()

# multiple tests check cannot login with bad credentials


@pytest.mark.parametrize(('email', 'password', 'message'), (
    ('1', 's', b'Unknown email.'),
    ('david.baux@inserm.fr', 'r', b'Incorrect password.'),
))
def test_login_validate_input(client, email, password, message):
    response = client.post(
        '/auth/login',
        data={'email': email, 'password': password}
    )
    print(response.get_data())
    assert message in response.get_data()

# test activation


@pytest.mark.parametrize(('mobiuser_id', 'api_key', 'message'), (
    (12, 'J9gKDvkEKktuv7t3dRB7tGopiusyCa9WQkwVEy1tDzc', b'API key and user id do not seem to fit'),
    (11, 'J9gKDvkEKktuv7t3dRB7tGopiusyCa9WQkwVEy1tDzc',  b'API key and user id do not seem to fit'),
    (12, '_jO9AZj62Y71MUByR-W41tdHIwJOKeqTLOya8WBoFF0', b'Please Log in if already registered and if you want to trace your variants')
))
def test_activate(client, mobiuser_id, api_key, message):
    response = client.get(
        '/auth/activate/{0}/{1}'.format(mobiuser_id, api_key)
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
    assert client.get('/auth/profile/{}'.format(mobiuser_id)).status_code == 302
    with app.app_context():
        response = client.get('/auth/profile/{}'.format(mobiuser_id), follow_redirects=True)
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        # following does not work - as if login does not work properly?
        # db_pool, db = get_db()
        # curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # curs.execute(
        #     "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        # )
        # res = curs.fetchone()
        # auth.login('mobidetails.iurc@gmail.com', res['password'])
        # response = client.get('/auth/profile/{}'.format(mobiuser_id))
        # print(response.get_data())
        # assert message in response.get_data()

# test log out redirect to homepage


def test_logout(client):
    response = client.get('/auth/logout')
    print(response.headers['Location'])
    assert 'http://localhost/' == response.headers['Location']
    # assert b'Homepage' in response.get_data()

# test forgot my password form


@pytest.mark.parametrize(('mobiuser_email', 'message'), (
    ('david.bauxinserm.fr', b'The email address does not look valid.'),
    ('david@insermfr', b'The email address does not look valid.'),
    ('david@inserm.fr', b'seems to be unknown by the system.'),
    ('david.baux@inserm.fr', b'Please check your e-mail inbox'),
))
def test_forgot_pass(client, mobiuser_email, message):
    response = client.post(
        '/auth/forgot_pass',
        data={'email': mobiuser_email}
    )
    print(response.get_data())
    assert message in response.get_data()

# test reset password


@pytest.mark.parametrize(('mobiuser_id', 'api_key', 'timestamp', 'message'), (
    (2, 'xLeeX6_tD3flHnI__Rc4P1PqklR2Sm8aFs8PXrMrE6s', None, b'API key and user id do not seem to fit.'),
    ('test', 'xLeeX6_tD3flHnI__Rc4P1PqklR2Sm8aFs8PXrMrE6s', None, b'Some parameters are not legal'),
    (1, 'xLeeX6_tD3flHnI__Rc4P1PqklR2Sm8aFs8PXrMrE6s', None, b'Please fill in the form to reset your password with a new one.'),
    (1, 'xLeeX6_tD3flHnI__Rc4P1PqklR2Sm8aFs8PXrMrE6s', '593612854.360794', b'This link is outdated.'),
    (1, 'xLeeX6_tD3flHnI__Rc4P1PqklR2Sm8aFs8PXrMrE6s', '2593612854.360794', b'This link is outdated.'),
))
def test_reset_password(client, mobiuser_id, api_key, timestamp, message):
    if timestamp is None:
        timestamp = datetime.timestamp(datetime.now())
    response = client.get(
        '/auth/reset_password?mobiuser_id={0}&api_key={1}&ts={2}'.format(
            mobiuser_id,
            api_key,
            timestamp
        )
    )
    # print(response.get_data())
    assert message in response.get_data()

# test variant list


@pytest.mark.parametrize(('list_name', 'http_code'), (
    ('mobidetails_list_1', 200),
    ('test', 404),
))
def test_variant_list(client, list_name, http_code):
    assert client.get(
            '/auth/variant_list/{}'.format(
                list_name,
            )
        ).status_code == http_code
