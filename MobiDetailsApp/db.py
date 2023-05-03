import os
import psycopg2
import psycopg2.extras
# requires MobiDetails config module + database.ini file
from . import md_utilities, configuration
import click
import threading
from flask import g, current_app as app
from flask.cli import with_appcontext

pool_params = configuration.mdconfig(section='psycopg2')
# semaphore is used in case the max_conn param is raised: we wait for a conn to come back
poolSemaphore = threading.Semaphore(int(pool_params['max_pool_conn']))


def get_db():
    if 'db' not in g:
        # print('App:{0}'.format(app.config))
        try:
            # use the Semaphore
            poolSemaphore.acquire(blocking=True)
            # read connection parameters
            g.db = app.config['POSTGRESQL_POOL'].getconn()
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
        return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        app.config['POSTGRESQL_POOL'].putconn(db)
        poolSemaphore.release()


def init_db():
    db = get_db()
    curs = db.cursor()
    with open(os.getcwd() + "/MobiDetailsApp/sql/MobiDetails.sql", "r") as sql_file:
        curs.execute(sql_file.read())


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
