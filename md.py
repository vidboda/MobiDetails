from flask import Flask, escape, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import func, distinct

#app definition and db connection
app =  Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://mobidetails:@localhost/mobidetails'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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


@app.route('/MD')
def homepage(mduser='Public user'):
	Base = automap_base()
	Base.prepare(db.engine, reflect=True)
	#VarF = Base.classes.variant_feature
	Gene = Base.classes.gene
	nb_genes = db.session.query(func.count(distinct(Gene.name[0]))).count()
	#nb_vars = db.session.query(VarF).count()
	nb_isoforms = db.session.query(func.count(Gene.name)).count()
	return render_template('homepage.html', nb_genes=nb_genes, nb_isoforms=nb_isoforms, mduser=mduser)

@app.route('/MD/about')
def aboutpage():
	return render_template('about.html')
	