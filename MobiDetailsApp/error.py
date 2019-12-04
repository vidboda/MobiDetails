from flask import render_template, Blueprint, current_app as app
#from MobiDetailsApp import current_app as app#, db
###################
###Deprecated errors are handled in __init__.py
###################



bp = Blueprint('error', __name__)

@bp.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    #db.session.rollback()
    return render_template('errors/500.html'), 500

@bp.errorhandler(403)
def forbidden_error(error):
	return render_template('errors/403.html'), 403