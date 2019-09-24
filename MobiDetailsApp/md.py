#import os
import re
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
import psycopg2
import psycopg2.extras
import tabix
# import json
# import urllib3

from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db
from . import md_utilities

bp = Blueprint('md', __name__)
#to be modified when in prod - modify pythonpath and use venv with mod_wsgi
#https://stackoverflow.com/questions/10342114/how-to-set-pythonpath-on-web-server
#https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/





######################################################################
#web app - index
@bp.route('/')
def index():
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
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
	return render_template('md/about.html', urls=md_utilities.urls, local_files=md_utilities.local_files)


######################################################################
#web app - gene
@bp.route('/gene/<string:gene_name>', methods=['GET', 'POST'])
def gene(gene_name=None):
	if gene is None:
		return render_template('unknown.html')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#main isoform?
	curs.execute(
		"SELECT * FROM gene WHERE name[1] = '{0}' AND number_of_exons = (SELECT MAX(number_of_exons) FROM gene WHERE name[1] = '{0}')".format(gene_name)
	)
	main = curs.fetchone()
	if main is not None:
		curs.execute(
			"SELECT * FROM gene WHERE name[1] = '{}'".format(gene_name)
		)#get all isoforms
		result_all = curs.fetchall()
		if result_all is not None:
			#get annotations
			curs.execute(
				"SELECT * FROM gene_annotation WHERE gene_name[1] = '{}'".format(gene_name)
			)
			annot = curs.fetchone();
			return render_template('md/gene.html', urls=md_utilities.urls, gene=gene_name, main_iso=main, res=result_all, annotations=annot)
		else:
			return render_template('md/unknown.html', query=gene_name)
	else:
		return render_template('md/unknown.html', query=gene_name)
	
######################################################################
#web app - all genes
@bp.route('/genes')
def genes():
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT DISTINCT(name[1]) AS hgnc FROM gene ORDER BY name[1]"
	)
	genes = curs.fetchall()
	if genes is not None:
		return render_template('md/genes.html', genes=genes)
	else:
		return render_template('md/unknown.html')

######################################################################
#web app - variants in genes
@bp.route('/vars/<string:gene_name>', methods=['GET', 'POST'])
def vars(gene_name=None):
	if gene is None:
		return render_template('unknown.html', query='No gene provided')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#error = None
	#main isoform?
	curs.execute(
		"SELECT * FROM gene WHERE name[1] = '{0}' AND number_of_exons = (SELECT MAX(number_of_exons) FROM gene WHERE name[1] = '{0}')".format(gene_name)
	)
	main = curs.fetchone()
	if main is not None:
		curs.execute(
			"SELECT * FROM variant_feature WHERE gene_name[1] = '{}' ORDER BY prot_type, ng_name".format(gene_name)
		)
		variants = curs.fetchall()
		#if vars_type is not None:
		return render_template('md/vars.html', urls=md_utilities.urls, gene=gene_name, variants=variants, gene_info=main)
	else:
		return render_template('md/unknown.html', query=gene_name)

######################################################################
#web app - variant
@bp.route('/variant/<int:variant_id>', methods=['GET', 'POST'])
def variant(variant_id=None):
	if variant_id is None:
		return render_template('unknown.html', query='No variant provided')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	# get all variant_features and gene info
	curs.execute(
		"SELECT * FROM variant_feature a, gene b WHERE a.gene_name = b.name AND a.id = '{0}'".format(variant_id)
	)
	variant_features = curs.fetchone()
	# get variant info
	curs.execute(
		"SELECT * FROM variant WHERE feature_id = '{0}'".format(variant_id)
	)
	variant = curs.fetchall()
	# compute position / splice sites
	if variant_features['variant_size'] < 50:
		for var in variant:
			if var['genome_version'] == 'hg38':
				#get a tuple ['site_type', 'dist(bp)']
				pos_splice_site = md_utilities.get_pos_splice_site(db, var['pos'], variant_features['start_segment_type'], variant_features['start_segment_number'], variant_features['gene_name'])
			if variant_features['start_segment_type'] != variant_features['end_segment_type'] or variant_features['start_segment_number'] != variant_features['end_segment_number']:
				#indels > 1 bp
				#get a tuple ['site_type', 'dist(bp)']
				pos_splice_site_second = md_utilities.get_pos_splice_site(var['pos'], variant_features['end_segment_type'], variant_features['end_segment_number'], variant_features['gene_name'])
				if pos_splice_site[1] > pos_splice_site_second[1]:
					#pos_splice_site_second nearest from splice site
					pos_splice_site = pos_splice_site_second
		#compute position in domain
		#1st get aa pos
		aa_pos = md_utilities.get_aa_position(variant_features['p_name'])
		curs.execute(
			"SELECT * FROM protein_domain WHERE gene_name[2] = '{0}' AND (('{1}' BETWEEN aa_start AND aa_end) OR ('{2}' BETWEEN aa_start AND aa_end));".format(variant_features['gene_name'][1], aa_pos[0], aa_pos[1])
		)
		domain = curs.fetchall()
	
	#dict for annotations
	annot = {}
	
	# clinvar search & gnomad
	# tabix searches in fact
	
	for var in variant:
		if var['genome_version'] == 'hg38':
			#clinvar
			record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38'][0], var)
			if isinstance(record, str):
				annot['clinsig'] = record
			else:
				annot['clinvar_id'] = record[2]
				match_object =  re.match('CLNSIG=(.+);', record[7])
				if match_object:
					annot['clinsig'] = match_object.group(1)
			#dbNSFP
			# if variant_features['prot_type'] == 'missense':				
			# 	dbNSFP_file = md_utilities.get_dbNSFP_file(variant_features['chr'])
			# 	#print(dbNSFP_file)
			# 	record = md_utilities.get_value_from_tabix_file('dbNSFP', dbNSFP_file, var)
			# 	if isinstance(record, str):
			# 		annot['dbNSFP'] = record
			# 	else:
			# 		#first: get enst we're dealing with
			# 		i=0
			# 		enst_list = re.split(';', record['14'])
			# 		for enst in enst_list:
			# 			if variant_features['enst'] == enst:
			# 				transcript_index = i
			# 				i += 1
			# 		#then iterate for each score of interest, e.g.  sift..
			# 		#missense:
			# 		#sift4g
			# 		annot['sift4g_score'] = re.split(';', record['39'])[i]
			# 		annot['sift4g_color'] = get_preditor_single_threshold_color(1-annot['sift4g_score'], 'sift')
			#litvar
			
					
		elif var['genome_version'] == 'hg19':
			#gnomad ex
			record = md_utilities.get_value_from_tabix_file('gnomAD exome', md_utilities.local_files['gnomad_exome'][0], var)
			if isinstance(record, str):
				annot['gnomad_exome_all'] = record
			else:
				annot['gnomad_exome_all'] = record[5]
			#gnomad ge
			record = md_utilities.get_value_from_tabix_file('gnomAD genome', md_utilities.local_files['gnomad_genome'][0], var)
			if isinstance(record, str):
				annot['gnomad_genome_all'] = record
			else:
				annot['gnomad_genome_all'] = record[5]
			#dbscSNV
			record = md_utilities.get_value_from_tabix_file('dbscSNV', md_utilities.local_files['dbscsnv'][0], var)
			if isinstance(record, str):
				annot['dbscsnv_ada'] = record
				annot['dbscsnv_rf'] = record
			else:
				annot['dbscsnv_ada'] = record[14]
				annot['dbscsnv_ada_color'] = get_preditor_single_threshold_color(float(annot['dbscsnv_ada']), 'dbscsnv')
				annot['dbscsnv_rf'] = record[15]
				annot['dbscsnv_rf_color'] = get_preditor_single_threshold_color(float(annot['dbscsnv_rf']), 'dbscsnv')
			#spliceai
			if variant_features['dna_type'] == 'substitution':
				record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai'][0], var)
				if isinstance(record, str):
					annot['spliceai'] = record
				else:
					spliceais = re.split(';', record[7])
					for spliceai in spliceais:
						#DIST=-73;DS_AG=0.0002;DS_AL=0.0000;DS_DG=0.0000;DS_DL=0.0000;DP_AG=14;DP_AL=-3;DP_DG=9;DP_DL=15
						match_object = re.match('(\w+)=(.+)', spliceai)
						#put value in annot dict
						identifier = "spliceai_{}".format(match_object.group(1))
						annot[identifier] = match_object.group(2)
						#put also html color corresponging to value
						if re.match('spliceai_DS_', identifier):
							id_color = "{}_color".format(identifier)
							annot[id_color] = md_utilities.get_spliceai_color(float(annot[identifier]))
			

	print(annot)
	
	return render_template('md/variant.html', aa_pos=aa_pos, urls=md_utilities.urls, variant_features=variant_features, variant=variant, pos_splice=pos_splice_site, protein_domain=domain, annot=annot)


######################################################################
#web app - search engine
@bp.route('/search_engine', methods=['POST'])
def search_engine():
	query_engine = request.form['search']
	#query_engine = query_engine.upper()
	if query_engine is not None:
		pattern = ''
		query_type = ''
		sql_table = 'variant_feature'
		col_names = 'id'
		# for aa in one2three.keys():
		#     aas += "{0}, ".format(aa)
		# return render_template('md/search_engine.html', query=aas)
		#deal w/ protein names
	
		match_object = re.match('^([a-zA-Z]{1})(\d+)([a-zA-Z\*]{1})$', query_engine) #e.g. R34X
		if match_object:
			query_type = 'p_name'
			pattern = md_utilities.one2three_fct(query_engine)
		elif re.match('^p\..+', query_engine):
			query_type = 'p_name'
			var = md_utilities.clean_var_name(query_engine)
			match_object = re.match('^(\w{1})(\d+)([\w\*]{1})$', var) #e.g. p.R34X
			match_object_long = re.match('^(\w{1})(\d+_)(\w{1})(\d+.+)$', var) #e.g. p.R34_E68del
			if match_object:
				pattern = md_utilities.one2three_fct(var)
			else:
				pattern = re.sub('X', '*', var)
		elif re.match('[Cc][Hh][Rr][\dXYM]{1,2}:g\..+', query_engine): #deal w/ genomic
			sql_table = 'variant'
			query_type = 'g_name'
			col_names = 'feature_id'
			match_object = re.match('[Cc][Hh][Rr][\dXYM]{1,2}:g\.(.+)', query_engine)
			pattern = match_object.group(1)
		elif re.match('^g\..+', query_engine):#g. ng dna vars
			query_type = 'ng_name'
			pattern = md_utilities.clean_var_name(query_engine)
		elif re.match('^c\..+', query_engine):#c. dna vars
			query_type = 'c_name'
			pattern = md_utilities.clean_var_name(query_engine)
		elif re.match('^[A-Z0-9]+$', query_engine):#genes
			sql_table = 'gene'
			query_type = 'name[1]'
			col_names = 'name'
			pattern = query_engine
		else:
			return render_template('md/unknown.html', query=query_engine, transformed_query=pattern)
		
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		#sql_query = "SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
		#return render_template('md/search_engine.html', query=text)
		#a little bit of formatting
		if re.match('variant', sql_table) and re.match('>', pattern):
			#upper for the end of the variant, lwer for genomic chr
			var_match = re.match('^(.*)(\.+)([ACTG]>[ACTG])$')
			pattern = var_match.group(1).lower() + var_match.group(2) + var_match.group(1).upper()
		curs.execute(
			"SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
		)
		result = curs.fetchone()
		if result is None:
			return render_template('md/unknown.html', query=query_engine, transformed_query="SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern))
		elif sql_table == 'gene':
			return redirect(url_for('md.gene', gene_name=result[col_names][0]))
		else:
			return redirect(url_for('md.variant', variant_id=result[col_names]))
		
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