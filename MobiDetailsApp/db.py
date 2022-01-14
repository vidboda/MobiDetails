import os
import psycopg2
import psycopg2.extras
# requires MobiDetails config module + database.ini file
from . import md_utilities
import click
from flask import g, current_app as app
from flask.cli import with_appcontext


def get_db():
    if 'db' not in g:
        # print('App:{0}'.format(app.config))
        try:
            # read connection parameters
            g.db = app.config['POSTGRESQL_POOL'].getconn()
            # params = configuration.mdconfig()
            # g.db = psycopg2.connect(**params)
        except (Exception, psycopg2.DatabaseError) as error:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    '<p>DB connection issue {0}<br /> - from {1}</p>'.format(
                        error,
                        os.path.basename(__file__)
                    )
                ),
                '[MobiDetails - DB Error]'
            )
            print(error)
        return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        app.config['POSTGRESQL_POOL'].putconn(db)
        # print('rendered back db connection')
        # db.close()


def init_db():
    db = get_db()
    curs = db.cursor()
    # print(os.getcwd())
    curs.execute(open(os.getcwd() + "/MobiDetailsApp/sql/MobiDetails.sql", "r").read())
    # with current_app.open_resource('sql/MobiDetails.sql') as f:
    #    db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
