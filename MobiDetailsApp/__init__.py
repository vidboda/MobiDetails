import os


from flask import Flask

def create_app(test_config=None):
	app =  Flask(__name__)
	if test_config is None:
		# load the instance config, if it exists, when not testing
		app.config.from_pyfile('config.py', silent=True)
		#app.config.from_object(os.environ['APP_SETTINGS'])
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
	app.add_url_rule('/', endpoint='index')
	
	# a simple page that says hello
	#@app.route('/hello')
	#def hello():
	#	return 'Hello, World!'
	
	
	return app