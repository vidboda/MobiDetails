import os
import re
from configparser import ConfigParser

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
	md_params = {}
	if parser.has_section(section):
		params = parser.items(section)
		for param in params:
			md_params[param[0]] = param[1]

	else:
		md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails error', '<p>Section {0} not found in the {1} file <br /> - from {2}</p>'.format(section, filename, os.path.basename(__file__)), '[MobiDetails - Config Error]'))
		raise Exception('Section {0} not found in the {1} file'.format(section, filename))

	return md_params

#jinja custom filter
def match(value, regexp):
	return re.match(regexp, value)
# def email_check_key(filename=dir_path + '/sql/database.ini', section='emailcheck'):
# 	# create a parser
# 	parser = ConfigParser()
# 	# read config file
# 	parser.read(filename) 
# 	# get section
# 	if parser.has_section(section):
# 		params = parser.items(section)
# 		for param in params:
# 			if param[0] == 'apikey':
# 				return param[1]
# 	else:
# 		raise Exception('Section {0} not found in the {1} file'.format('emailcheck', dir_path + '/sql/database.ini'))
# 	
# def email_config(filename=dir_path + '/sql/database.ini', section='emailauth'):
# 	# create a parser
# 	parser = ConfigParser()
# 	# read config file
# 	parser.read(filename) 
# 	# get section
# 	if parser.has_section(section):
# 		email_params = {}
# 		params =  parser.items(section)
# 		for param in params:
# 			email_params[param[0]] = param[1]
# 				
				
7
	
	
