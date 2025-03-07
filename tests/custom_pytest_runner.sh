#!/usr/bin/bash

# /usr/bin/python3.6 -m pytest --cov=MobiDetailsApp --cov-report xml:coverage.xml --cov-report term
/var/www/MobiDetails/venv/bin/python -m pytest --cov=MobiDetailsApp --cov-report xml:coverage.xml --cov-report term
