import os
import re
from . import configuration  # lgtm [py/import-own-module]
from flask import Flask, render_template, url_for, flash, redirect, get_flashed_messages, request
from flask_mail import Mail
from flask_cors import CORS
# from logging.handlers import RotatingFileHandler
# https://flask-wtf.readthedocs.io/en/stable/csrf.html
from flask_wtf.csrf import CSRFProtect, CSRFError
# https://blog.miguelgrinberg.com/post/cookie-security-for-flask-applications
from flask_paranoid import Paranoid
from psycopg2 import pool

mail = Mail()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static')
    # https://github.com/igvteam/igv.js/issues/1654
    @app.after_request
    def remove_header(response):
        # remove gzip content-encoding when loading partial bedgraphs
        # bgzip is not gzip, flask should not add these headers
        # if response.status_code == 206:
        # issue: on gene page the bedgraph is fully loaded, then
        # remove header for bedgraph.gz and genome.gz files
        if re.search('(bedGraph|fa).gz$', request.url):
            del response.headers['content-encoding']
            del response.headers['content-disposition']
        return response
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('sql/md.cfg', silent=False)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    # Initiate database connection pool
    params = configuration.mdconfig()
    pool_params = configuration.mdconfig(section='psycopg2')
    app.config['POSTGRESQL_POOL'] = pool.ThreadedConnectionPool(
        pool_params['min_pool_conn'],
        pool_params['max_pool_conn'],
        user=params['user'],
        password=params['password'],
        host=params['host'],
        port=params['port'],
        database=params['database']
    )
    mail.init_app(app)
    csrf.init_app(app)
    paranoid = Paranoid(app)
    paranoid.redirect_view = 'md.index'
    # cors
    # for swaggerUI
    # https://idratherbewriting.com/learnapidoc/pubapis_swagger.html
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    # errors
    app.register_error_handler(403, forbidden_error)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)
    app.register_error_handler(405, not_allowed_error)
    app.register_error_handler(413, request_entity_too_large_error)
    app.register_error_handler(CSRFError, csrf_error)
    # define custom jinja filters
    app.jinja_env.filters['match'] = configuration.match
    app.jinja_env.filters['match_multiline'] = configuration.match_multiline
    # define global jina variable for static full paths - to be used later?
    # app.add_template_global(name='SERVER_NAME', f=app.config['SERVER_NAME'])
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        # https://flask.palletsprojects.com/en/2.3.x/tutorial/factory/
        pass
    # somehow still used by pytest
    from . import db
    db.init_app(app)
    # load blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    from . import md
    app.register_blueprint(md.bp)
    from . import ajax
    app.register_blueprint(ajax.bp)
    from . import api
    csrf.exempt(api.bp)
    app.register_blueprint(api.bp)
    from . import static_route
    app.register_blueprint(static_route.bp)
    from . import upload
    app.register_blueprint(upload.bp)
    
    app.add_url_rule('/', endpoint='index')
    if app.debug:
        print(app.config)
    return app


def not_found_error(error):
    return render_template('errors/404.html'), 404


def internal_error(error):
    # db.session.rollback()
    return render_template('errors/500.html'), 500


def forbidden_error(error):
    return render_template('errors/403.html'), 403


def not_allowed_error(error):
    return render_template('errors/405.html'), 405


def request_entity_too_large_error(error):
    return render_template('errors/413.html'), 413


def csrf_error(error):
    flashed_messages = get_flashed_messages()
    csrf_message = 0
    if flashed_messages:
        for flashed_message in flashed_messages:
            if re.search('This typically means that you need to reload a fresh page and resubmit your query', flashed_message):
                csrf_message = 1
    if csrf_message == 0:
        flash('{0} : {1}. This typically means that you need to reload a fresh page and resubmit your query.'.format(error.name, error.description), 'w3-pale-red')
    return redirect(url_for('md.index'))