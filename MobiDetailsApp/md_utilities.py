import re
import psycopg2
import psycopg2.extras
from MobiDetailsApp.db import get_db


one2three = {
	'A': 'Ala', 'C': 'Cys', 'D': 'Asp', 'E': 'Glu', 'F': 'Phe', 'G': 'Gly', 'H': 'His', 'I': 'Ile', 'K': 'Lys', 'L': 'Leu', 'M': 'Met', 'N': 'Asn', 'P': 'Pro', 'Q': 'Gln', 'R': 'Arg', 'S': 'Ser', 'T': 'Thr', 'V': 'Val', 'W': 'Trp', 'Y': 'Tyr', 'del': 'del', 'X': '*', '*': '*', '=': '='
}
three2one = {
	'Ala': 'A', 'Cys': 'C', 'Asp': 'D', 'Glu': 'E', 'Phe': 'F', 'Gly': 'G', 'His': 'H', 'Ile': 'I', 'Lys': 'K', 'Leu': 'L', 'Met': 'M', 'Asn': 'N', 'Pro': 'P', 'Gln': 'Q', 'Arg': 'R', 'Ser': 'S', 'Thr': 'T', 'Val': 'V', 'Trp': 'W', 'Tyr': 'Y', 'Del': 'del', 'X': '*', '*': '*', 'Ter': '*', '=': '='
}


def clean_var_name(variant):
	variant = re.sub('^[cpg]\.', '', variant)
	variant = re.sub(r'\(', '', variant)
	variant = re.sub(r'\)', '', variant)
	return variant

def three2one_fct(var):
	var = clean_var_name(var)
	match_object = re.match('^(\w{3})(\d+)(\w{3}|[X\*=])$', var)
	if match_object:
		return three2one[match_object.group(1).capitalize()] + match_object.group(2) + three2one[match_object.group(3).capitalize()]
	match_object = re.match('^(\w{3})(\d+_)(\w{3})(\d+.+)$', var)
	if match_object:
		return three2one[match_object.group(1)].capitalize() + match_object.group(2) + three2one[match_object.group(3)].capitalize() + match_object.group(4)
	
def one2three_fct(var):
	var = clean_var_name(var)
	match_object = re.match('^(\w{1})(\d+)([\w\*=]{1})$', var)
	if match_object:
		return one2three[match_object.group(1).capitalize()] + match_object.group(2) + one2three[match_object.group(3).capitalize()]
	match_object = re.match('^(\w{1})(\d+_)(\w{1})(\d+.+)$', var)
	if match_object:
		return one2three[match_object.group(1).capitalize()] + match_object.group(2) + one2three[match_object.group(3).capitalize()] + match_object.group(4)
	
#jinja custom filter
def match(value, regexp):
	return re.match(regexp, value)

#compute position relative to nearest splice site
def get_pos_splice_site(db, pos, seg_type, seg_num, gene, genome='hg38'):
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#main isoform?
	curs.execute(
		"SELECT segment_start, segment_end FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND type = '{3}' AND number = '{4}'".format(genome, gene[0], gene[1], seg_type, seg_num, genome)
	)
	positions = curs.fetchone()
	if positions is not None:
		print("{0}-{1}-{2}".format(positions['segment_start'],pos,positions['segment_end']))
		#return min(abs(int(positions['segment_end'])-int(pos)+1), abs(int(positions['segment_start'])-int(pos)+1))
		if abs(int(positions['segment_end'])-int(pos)+1) <= abs(int(positions['segment_start'])-int(pos)+1):
			#near from segment_end
			#if seg_type == 'exon':
			#always exons!!!!
			return ['donor', abs(int(positions['segment_end'])-int(pos))+1]
			#else:
			#	return ['acceptor', abs(int(positions['segment_end'])-int(pos))+1]
		else:
			#near from segment_start
			#if seg_type == 'exon':
			return ['acceptor', abs(int(positions['segment_start'])-int(pos))+1]
			#else:
			#	return ['donor', abs(int(positions['segment_start'])-int(pos))+1]
			
#get aa position fomr hgvs p. (3 letter)
def get_aa_position(hgvs_p):
	match_object = re.match('^\w{3}(\d+)[^\d]+$', hgvs_p)
	if match_object:
		return match_object.group(1)
	match_object = re.match('^\w{3}(\d+)_\w{3}(\d+)[^\d]+$', hgvs_p)
	if match_object:
		return "{0}_{1}".format(match_object.group(1), match_object.group(2))