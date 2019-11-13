import pytest
from flask import g, session
from MobiDetailsApp import error

def test_not_found_error(client):
	assert client.get('/genesfgsrtg').status_code == 404
def test_internal_error(client, app):
	with app.app_context():
		response = error.internal_error('500')
		assert response.status_code  == 500