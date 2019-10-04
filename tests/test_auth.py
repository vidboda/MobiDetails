import pytest
from flask import g, session
from MobiDetailsApp.db import get_db


def test_register(client, app):
	#test register returns no error
	assert client.get('/auth/register').status_code == 200
	response = client.post(
	'/auth/register', data={'username': 'davidbaux', 'password': 'a', 'country': 'a', 'institute': 'a', 'email': 'david.baux@inserm.fr',}
	)
	assert response.status_code  == 200

	#test db returns a value
	with app.app_context():
		db = get_db()
		curs = db.cursor()
		curs.execute(
			"SELECT * FROM mobiuser WHERE username = 'davidbaux'",
		)
		res = curs.fetchone()
		assert res is not None

#multiple tests to check known username and email returns a message
@pytest.mark.parametrize(('username', 'password', 'email', 'message'), (
	('djsdlm', 'ss9kghgf', 'david.baux@inserm.fr', b'is already registered.'),
	('davidbaux', 'ss9kghgf', 'kevin@inserm.fr', b'is already registered.'),
	('1', 's', 'v', b'Username should be at least 5 characters.'),
	('djsdlm', 's', 'v', b'Password should be at least 8 characters and mix at least letters and numbers.'),
	('djsdlm', 'ss9kghgf', 'kevin@inserm.f', b'The email address does not look valid.')
))
def test_register_validate_input(client, username, password, email, message):
	response = client.post(
		'/auth/register',
		data={'username': username, 'password': password, 'country': 'a', 'institute': 'a', 'email': email}
	)
	print(response.get_data())
	assert message in response.get_data()

@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('1', 's', b'Incorrect username.'),
    ('davidb', 'r', b'Incorrect password.')
))
#mutliple tests check cannot login with bad credentials
def test_login_validate_input(client, username, password, message):
	response = client.post(
		'/auth/login',
		data={'username': username, 'password': password}
	)
	print(response.get_data())
	assert message in response.get_data()
#test log out redirect to homepage
def test_logout(client):
	response = client.get('/auth/logout')
	#print(response.headers['Location'])
	assert 'http://localhost/' == response.headers['Location']
	#assert b'Homepage' in response.get_data()