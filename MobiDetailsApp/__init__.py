import os
from . import config
from flask import Flask, render_template
from flask_mail import Mail
from flask_cors import CORS
from logging.handlers import RotatingFileHandler
import logging

mail = Mail()


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static')
    # config flaskmail
    params = config.mdconfig(section='email_auth')
    app.config.update(
        DEBUG=True,
        # EMAIL SETTINGS
        MAIL_SERVER=params['mail_server'],
        MAIL_PORT=params['mail_port'],
        MAIL_USE_TLS=params['mail_use_tls'],
        MAIL_USERNAME=params['mail_username'],
        MAIL_PASSWORD=params['mail_password'],
        MAIL_DEFAULT_SENDER=params['mail_default_sender']
    )

    mail.init_app(app)
    # cors
    # for swaggerUI
    # https://idratherbewriting.com/learnapidoc/pubapis_swagger.html
    #cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
    # errors
    app.register_error_handler(403, forbidden_error)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)
    app.register_error_handler(405, not_allowed_error)
    # define custom jinja filters
    app.jinja_env.filters['match'] = config.match
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
        # app.config.from_object(os.environ['APP_SETTINGS'])
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
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
    app.register_blueprint(api.bp)    
    from . import static_route
    app.register_blueprint(static_route.bp)
    
    # from . import error
    # app.register_blueprint(error.bp)
    app.add_url_rule('/', endpoint='index')
    
    # a simple page that says hello
    # @app.route('/factory_test')
    # def hello():
    #     return 'Flask factory ok!'
    # 
    if not app.debug:
        
        # logging into a file (from https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-vii-error-handling)
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/mobidetails.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    
        app.logger.setLevel(logging.INFO)
        app.logger.info('Mobidetails startup')
    
    
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