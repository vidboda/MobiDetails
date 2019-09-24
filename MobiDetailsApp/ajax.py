import os
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db
from . import md_utilities

import psycopg2
import psycopg2.extras
import json
import urllib3

bp = Blueprint('ajax', __name__)



######################################################################
#web app - ajax for litvar
@bp.route('/litVar', methods=['POST'])
def litvar():
	rsid = request.form['rsid']
	if rsid is not None:
		http = urllib3.PoolManager()
		litvar_url = "{0}{1}%23%23%22%5D%7D".format(md_utilities.urls['ncbi_litvar_api'], rsid)
		litvar_data = json.loads(http.request('GET', litvar_url).data.decode('utf-8'))
		#print (litvar_url)
		return render_template('ajax/litvar.html', urls=md_utilities.urls, pmids=litvar_data)

######################################################################
#web app - ajax for defgen export file
@bp.route('/defgen', methods=['POST'])
def defgen():
	variant_id = request.form['vfid']
	genome = request.form['genome']
	if variant_id is not None:
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		# get all variant_features and gene info
		curs.execute(
			"SELECT * FROM variant_feature a, variant b, gene c WHERE a.id = b.feature_id AND a.gene_name = c.name AND a.id = '{0}' AND b.genome_version = '{1}'".format(variant_id, genome)
		)
		vf = curs.fetchone()
		file_content = "GENE;VARIANT;A_ENREGISTRER;ETAT;RESULTAT;VARIANT_P;VARIANT_C;ENST;NM;POSITION_GENOMIQUE;CLASSESUR5;CLASSESUR3;COSMIC;RS;REFERENCES;CONSEQUENCES;COMMENTAIRE;CHROMOSOME;GENOME_REFERENCE;NOMENCLATURE_HGVS;LOCALISATION;SEQUENCE_REF;LOCUS;ALLELE1;ALLELE2\r\n"
		#"$res->{nom}[0];$res->{nom}[1].$res->{acc_version}:$res->{var};;;;$res->{hgvs_prot};$res->{var};$res->{enst};$res->{nom}[1].$res->{acc_version};$pos;$defgen_acmg;;;$res->{snp_id};;$res->{type_prot};;$chr;hg19;$res->{nom_g};$res->{type_segment} $res->{num_segment};;;;\r\n";
		file_content += "{0};{1}.{2}:c.{3};;;;p.{4};c.{3};{5}:{1}.{2};{6};{7};;;rs{8};;{9};;;chr{10};{11};chr{10}:g.{12};{13} {14};;;;\r\n".format(vf['gene_name'][0], vf['gene_name'][1], vf['nm_version'], vf['c_name'], vf['p_name'], vf['enst'], vf['pos'], vf['acmg_class'], vf['dbsnp_id'], vf['prot_type'], vf['chr'], genome, vf['g_name'], vf['start_segment_type'], vf['start_segment_number'])
		#print(file_content)
		app_path = os.path.dirname(os.path.realpath(__file__))
		file_loc = "defgen/{0}-{1}-{2}{3}-{4}.csv".format(genome, vf['chr'], vf['pos'], vf['pos_ref'], vf['pos_alt'])
		defgen_file = open("{0}/static/{1}".format(app_path, file_loc), "w")
		defgen_file.write(file_content)
		return render_template('ajax/defgen.html', variant="{0}.{1}:c.{2}".format(vf['gene_name'][1], vf['nm_version'], vf['c_name']), defgen_file=file_loc, genome=genome)