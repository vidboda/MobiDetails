import os
from configparser import ConfigParser

#SQLALCHEMY_DATABASE_URI='postgresql://mobidetails:bio%3Binfo1@localhost/mobidetails'
#SQLALCHEMY_TRACK_MODIFICATIONS=False

#SECRET_KEY='dev'
#get secret key from config file
dir_path = os.path.dirname(os.path.realpath(__file__))
parser = ConfigParser()
# read config file
parser.read(dir_path + '/sql/database.ini')
if parser.has_section('flask'):
	params = parser.items('flask')
	for param in params:
		if param[0] == 'secretkey':
			SECRET_KEY = param[1]
else:
	raise Exception('Section {0} not found in the {1} file'.format('flask', dir_path + '/sql/database.ini'))


#from http://www.postgresqltutorial.com/postgresql-python/connect/
def mdconfig(filename=dir_path + '/sql/database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename) 
    # get section, default to postgresql
    db_params = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_params[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
 
    return db_params

#https://medium.com/@dushan14/create-a-web-application-with-python-flask-postgresql-and-deploy-on-heroku-243d548335cc#
# class Config(object):
# 	DEBUG = False
# 	TESTING = False
# 	CSRF_ENABLED = True
# 	SECRET_KEY = 'this-really-needs-to-be-changed'
# 	#SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
# 
# 
# class ProductionConfig(Config):
# 	DEBUG = False
# 
# 
# class StagingConfig(Config):
# 	DEVELOPMENT = True
# 	DEBUG = True
# 
# 
# class DevelopmentConfig(Config):
# 	DEVELOPMENT = True
# 	DEBUG = True

