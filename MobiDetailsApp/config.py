import os
import re
from configparser import ConfigParser

# get secret key from config file
dir_path = os.path.dirname(os.path.realpath(__file__))
parser = ConfigParser()
#SESSION_COOKIE_SECURE = False
WTF_CSRF_TIME_LIMIT = None
# read config file
parser.read(dir_path + '/sql/database.ini')
if parser.has_section('flask'):
    params = parser.items('flask')
    for param in params:
        if param[0] == 'secretkey':
            SECRET_KEY = param[1]
        if param[0] == 'debug':
            DEBUG = param[1]
        elif param[0] == 'session_cookie_secure':
            if param[1] == 'False':
                SESSION_COOKIE_SECURE = False
            else:
                SESSION_COOKIE_SECURE = True
        elif param[0] == 'session_cookie_name':
            SESSION_COOKIE_NAME = param[1]
        elif param[0] == 'wtf_csrf_enabled':
            WTF_CSRF_ENABLED = param[1]
        elif param[0] == 'wtf_csrf_time_limit':
            WTF_CSRF_TIME_LIMIT = param[1]
else:
    raise Exception('Section {0} not found in the {1} file'.format(
        'flask',
        dir_path + '/sql/database.ini'
        )
    )

if parser.has_section('email_auth'):
    params = parser.items('email_auth')
    for param in params:
        if param[0] == 'mail_username':
            MAIL_USERNAME = param[1]
        elif param[0] == 'mail_password':
            MAIL_PASSWORD = param[1]
        elif param[0] == 'mail_server':
            MAIL_SERVER = param[1]
        elif param[0] == 'mail_use_tls':
            MAIL_USE_TLS = param[1]
        elif param[0] == 'mail_port':
            MAIL_PORT = param[1]
        elif param[0] == 'mail_default_sender':
            MAIL_DEFAULT_SENDER = param[1]
        elif param[0] == 'mail_error_recipient':
            MAIL_ERROR_RECIPIENT = param[1]
else:
    raise Exception('Section {0} not found in the {1} file'.format(
        'email_auth',
        dir_path + '/sql/database.ini'
        )
    )

# from http://www.postgresqltutorial.com/postgresql-python/connect/


def mdconfig(filename=dir_path + '/sql/database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)
    # get section, default to postgresql
    md_params = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            md_params[param[0]] = param[1]
    return md_params

# jinja custom filter


def match(value, regexp):
    return re.match(regexp, value)
