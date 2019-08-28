from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
import psycopg2
import psycopg2.extras

from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db

bp = Blueprint('md', __name__)
#to be modified when in prod - modify pythonpath and use venv with mod_wsgi
#https://stackoverflow.com/questions/10342114/how-to-set-pythonpath-on-web-server
#https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/




#web app - index
@bp.route('/')
def index():
	db = get_db()
	curs = g.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	error = None
	curs.execute(
		"SELECT COUNT(DISTINCT(name[1])) AS gene, COUNT(name) as transcript FROM gene"
	)
	res = curs.fetchone()
	if res is None:
		error = "There is a problem with the number of genes."
		flash(error)
	else:
		return render_template('md/index.html', nb_genes=res['gene'], nb_isoforms=res['transcript'])

#web app - about
@bp.route('/about')
def about():
	return render_template('md/about.html')

#1st attempt with SQLalchemy
#@app.route('/MD')
# def homepage(mduser='Public user'):
# 	#Base = automap_base()
# 	#Base.prepare(db.engine, reflect=True)
# 	#VarF = Base.classes.variant_feature
# 	Gene = MobiDetailsDB.classes.gene
# 	nb_genes = db.session.query(func.count(distinct(Gene.name[0]))).count()
# 	#nb_vars = db.session.query(VarF).count()
# 	nb_isoforms = db.session.query(func.count(Gene.name)).count()
# 	return render_template('md/homepage.html', nb_genes=nb_genes, nb_isoforms=nb_isoforms, mduser=mduser)
# 
# @app.route('/MD/about')
# def aboutpage():
# 	return render_template('md/about.html')
# 
# 
# #api
# 
# @app.route('/MD/api/gene_list')
# def gene_list():
# 	Gene = MobiDetailsDB.classes.gene
# 	#gene_list = Gene.query.filter.all()
# 	#below code displays all mehtods available for a given object
# 	object_methods = [method_name for method_name in dir(Gene)
# 		if callable(getattr(Gene, method_name))]
# 	
# 	return render_template('md/api.html', gene_list=object_methods)




#####below was the first draft to test flask - deprecated 08/2019
# from flask import Flask, escape, url_for, render_template
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.ext.automap import automap_base
# from sqlalchemy import func, distinct
#import sys
#sys.path.append('./sql/')
#import mdsecrets

#app definition and db connection
#app =  Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = mdsecrets.mddbms + '://' + mdsecrets.mdusername + ':' + mdsecrets.mdpassword + '@' + mdsecrets.mdhost + '/' + mdsecrets.mddb
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#db = SQLAlchemy(app)

#db Model instantiation
# class Gene(db.Model):
# 	__tablename__ = 'gene'
# 	name = Gene.c.name
# 	second_name = db.Column(db.String(20))
# 	chrom = db.Column('chr', db.String(2), nullable=False)
# 
# class MobiUser(db.Model):
# 	__tablename__ = 'mobiuser'
# 	
# 	id = db.Column(db.Integer, primary_key=True)
# 	email = db.Column(db.String(120), unique=True, nullable=False)
# 	first_name = db.Column(db.String(30))
# 	last_name = db.Column(db.String(30))
# 	institute = db.Column(db.String(100))
# 	country = db.Column(db.String(50))
# 
# 	def __repr__(self):
# 		return "<User (first_name='%s', last_name='%s', email='%s', institute='%s', country='%s')>" % (self.first_name, self.last_name, self.email, self.institute, self.country)

#SQLAlchemy allows automapping to existing database
#mapping useful tables for each view?
#MobiDetailsDB = automap_base()
#MobiDetailsDB.prepare(db.engine, reflect=True)