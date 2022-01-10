import os
from . import configuration
from flask import Flask, render_template
from flask_mail import Mail
from flask_cors import CORS
# from logging.handlers import RotatingFileHandler
# https://flask-wtf.readthedocs.io/en/stable/csrf.html
from flask_wtf.csrf import CSRFProtect
# https://blog.miguelgrinberg.com/post/cookie-security-for-flask-applications
from flask_paranoid import Paranoid
# import logging
from psycopg2 import pool

mail = Mail()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static')

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('sql/md.cfg', silent=False)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    # Initiate database connection pool
    params = configuration.mdconfig()
    app.config['POSTGRESQL_POOL'] = pool.ThreadedConnectionPool(
        1, 100,
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
    app.register_error_handler(413, reques_entity_too_large_error)
    # define custom jinja filters
    app.jinja_env.filters['match'] = configuration.match
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    from . import db
    db.init_app(app)
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
    # from . import error
    # app.register_blueprint(error.bp)
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


def reques_entity_too_large_error(error):
    return render_template('errors/413.html'), 413
