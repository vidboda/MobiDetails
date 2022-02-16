import os
import re
from configparser import ConfigParser

# from http://www.postgresqltutorial.com/postgresql-python/connect/
dir_path = os.path.dirname(os.path.realpath(__file__))
init_file = '/sql/database.ini'


def mdconfig(filename=dir_path + init_file, section='postgresql'):
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


def match_multiline(value, regexp):
    return re.match(regexp, value, re.DOTALL)
