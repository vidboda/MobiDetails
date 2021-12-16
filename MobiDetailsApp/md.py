import re
import os.path
import urllib3
import certifi
import json
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app as app
)
# from werkzeug.exceptions import abort
import psycopg2
import psycopg2.extras
# import tabix

# from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db, close_db
from . import md_utilities


bp = Blueprint('md', __name__)
# to be modified when in prod - modify pythonpath and use venv with mod_wsgi
# https://stackoverflow.com/questions/10342114/how-to-set-pythonpath-on-web-server
# https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/
# create a poolmanager
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
# -------------------------------------------------------------------
# web app - index


@bp.route('/')
def index():
    # print(app.config['RUN_MODE'])
    # check vv
    md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.check_vv_instance'))
    vv_instance = json.loads(
                    http.request(
                        'GET',
                        md_api_url
                    ).data.decode('utf-8')
                )
    # count genes
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        "SELECT COUNT(DISTINCT(name[1])) AS gene, COUNT(name) as \
        transcript FROM gene WHERE variant_creation = 'ok'"
    )
    res = curs.fetchone()
    if res is None:
        error = "There is a problem with the number of genes."
        flash(error, 'w3-pale-red')
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails PostGreSQL error',
                '<p>There is a problem with the number of genes.\
<br /> in {}</p>'.format(os.path.basename(__file__))
            ),
            '[MobiDetails - PostGreSQL Error]'
        )
    else:
        close_db()
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode(),
            nb_genes=res['gene'],
            nb_isoforms=res['transcript'],
            vv_instance=vv_instance
        )

# -------------------------------------------------------------------
# web app - about


@bp.route('/about')
def about():
    return render_template(
        'md/about.html',
        run_mode=md_utilities.get_running_mode(),
        urls=md_utilities.urls,
        local_files=md_utilities.local_files,
        external_tools=md_utilities.external_tools
    )

# -------------------------------------------------------------------
# web app - changelog


@bp.route('/changelog')
def changelog():
    return render_template(
        'md/changelog.html',
        run_mode=md_utilities.get_running_mode(),
        urls=md_utilities.urls
    )

# -------------------------------------------------------------------
# web app - gene


@bp.route('/gene/<string:gene_name>', methods=['GET', 'POST'])
def gene(gene_name=None):
    if gene_name is None:
        return render_template('md/unknown.html', query='No gene provided')
    elif re.search(r'[^\w-]', gene_name):
        return render_template('md/unknown.html', query=gene_name)
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # main isoform? now canonical is stored in db
    curs.execute(
        "SELECT * FROM gene WHERE name[1] = %s AND canonical = 't'",
        (gene_name,)
    )
    main = curs.fetchone()
    if main is not None:
        curs.execute(
            "SELECT * FROM gene WHERE name[1] = %s \
            ORDER BY number_of_exons DESC",
            (gene_name,)
        )  # get all isoforms
        result_all = curs.fetchall()
        num_iso = len(result_all)
        # get metadome json?
        enst_ver = {}
        # if not json metadome file on filesystem, create it in
        # radboud server, then next time get it - it will then be
        # available for future requests
        # if we have the main => next step
        if not os.path.isfile(
            '{0}{1}.json'.format(
                md_utilities.local_files['metadome']['abs_path'],
                main['enst']
            )
                ):
            for gene in result_all:
                if not os.path.isfile(
                    '{0}{1}.json'.format(
                        md_utilities.local_files['metadome']['abs_path'],
                        gene['enst']
                    )
                        ):
                    if gene['enst'] not in enst_ver:
                        # get enst versions in a dict
                        metad_ts = None
                        try:
                            # print('{0}get_transcripts/{1}'
                            # .format(md_utilities.urls['metadome_api'],
                            # gene['name'][0]))
                            metad_ts = json.loads(
                                        http.request(
                                            'GET',
                                            '{0}get_transcripts/{1}'.format(
                                                md_utilities.urls['metadome_api'],
                                                gene['name'][0]
                                            )
                                        ).data.decode('utf-8')
                            )
                            if metad_ts is not None and \
                                    'trancript_ids' in metad_ts:
                                for ts in metad_ts['trancript_ids']:
                                    if ts['has_protein_data']:
                                        match_obj = re.search(
                                            r'^(ENST\d+)\.\d',
                                            ts['gencode_id']
                                        )
                                        enst_ver[match_obj.group(1)] = ts['gencode_id']
                        except Exception as e:
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails API error',
                                    '<p>MetaDome first block code failed for \
gene {0} ({1})<br /> - from {2} with args: {3}</p>'.format(
                                        gene_name,
                                        gene['enst'],
                                        os.path.basename(__file__),
                                        e.args
                                    )
                                ),
                                '[MobiDetails - API Error]'
                            )
                    break

        # we check if data exist at metadome
        # we have a set of metadome transcripts
        for enst in enst_ver:
            # print('enst: {}'.format(enst_ver[enst]))
            # print('--{}--'.format(app.debug))
            # print(json.dumps({'transcript_id': enst_ver[enst]}))
            if not os.path.isfile(
                '{0}{1}.json'.format(
                    md_utilities.local_files['metadome']['abs_path'],
                    enst
                )
                    ):
                metad_data = None
                try:
                    metad_data = json.loads(
                                    http.request(
                                        'GET',
                                        '{0}status/{1}/'.format(
                                            md_utilities.urls['metadome_api'],
                                            enst_ver[enst])
                                    ).data.decode('utf-8')
                                )
                except Exception as e:
                    md_utilities.send_error_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails API error',
                            '<p>MetaDome second block code failed for gene \
{0} ({1})<br /> - from {2} with args: {3}</p>'.format(
                                gene_name,
                                enst,
                                os.path.basename(__file__),
                                e.args
                            )
                        ),
                        '[MobiDetails - API Error]'
                    )
                if metad_data is not None:
                    if metad_data['status'] == 'PENDING':
                        # get transcript_ids ?? coz of the version number
                        # send request to build visualization to metadome
                        vis_request = None
                        # find out how to get app object
                        try:
                            # enst_metadome = {transcript_id: enst_ver[enst]}
                            header = md_utilities.api_agent
                            header['Content-Type'] = 'application/json'
                            vis_request = json.loads(
                                            http.request(
                                                'POST',
                                                '{0}submit_visualization/'.format(
                                                    md_utilities.urls['metadome_api']
                                                ),
                                                # headers={'Content-Type': 'application/json'},
                                                headers=header,
                                                body=json.dumps(
                                                    {'transcript_id': enst_ver[enst]}
                                                )
                                            ).data.decode('utf-8')
                            )
                            if not app.debug:
                                app.logger.info(
                                    '{} submitted to metadome'.format(
                                        vis_request['transcript_id']
                                    )
                                )
                            else:
                                print('{} submitted to metadome'.format(
                                        vis_request['transcript_id']
                                    )
                                )
                        except Exception as e:
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails API error',
                                    '<p>Error with metadome submission for \
{0} ({1})<br /> - from {2} with args: {3}</p>'.format(
                                        gene_name,
                                        enst,
                                        os.path.basename(__file__),
                                        e.args
                                    )
                                ),
                                '[MobiDetails - API Error]'
                            )
                            # print('Error with metadome
                            # submission for {}'.format(enst))
                    elif metad_data['status'] == 'SUCCESS':
                        # get_request = None
                        try:
                            get_request = json.loads(
                                            http.request(
                                                'GET',
                                                '{0}result/{1}/'.format(
                                                    md_utilities.urls['metadome_api'],
                                                    enst_ver[enst]
                                                )
                                            ).data.decode('utf-8')
                                        )
                            # copy in file system
                            with open(
                                '{0}{1}.json'.format(
                                    md_utilities.local_files['metadome']['abs_path'],
                                    enst
                                ),
                                "w",
                                encoding='utf-8'
                            ) as metad_file:
                                json.dump(
                                    get_request,
                                    metad_file,
                                    ensure_ascii=False,
                                    indent=4
                                )
                            if not app.debug:
                                app.logger.info(
                                    'saving metadome {} into local file system'
                                    .format(enst_ver[enst])
                                )
                            else:
                                print(
                                    'saving metadome {} into local file system'
                                    .format(enst_ver[enst])
                                )
                        except Exception as e:
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails API error',
                                    '<p>Error with metadome file writing for \
{0} ({1})<br /> - from {2} with args: {3}</p>'.format(
                                        gene_name,
                                        enst,
                                        os.path.basename(__file__),
                                        e.args
                                    )
                                ),
                                '[MobiDetails - API Error]'
                            )
                            # print('error saving metadome json
                            # file for {}'.format(enst))
        if result_all is not None:
            # get annotations
            curs.execute(
                "SELECT * FROM gene_annotation WHERE gene_name[1] = %s",
                (gene_name,)
            )
            annot = curs.fetchone()
            if annot is None:
                annot = {'nognomad': 'No values in gnomAD'}
            curs.execute(
                "SELECT MAX(prot_size) as size FROM gene WHERE name[1] = %s",
                (gene_name,)
            )
            res_size = curs.fetchone()
            close_db()
            # get refseq select, mane, etc from vv json file
            no_vv_file = 0
            try:
                json_file = open('{0}{1}.json'.format(
                    md_utilities.local_files['variant_validator']['abs_path'],
                    gene_name
                ))
            except IOError:
                no_vv_file = 1
            if no_vv_file == 0:
                transcript_road_signs = {}
                vv_json = json.load(json_file)
                for vv_transcript in vv_json['transcripts']:
                    for res in result_all:
                        # need to check vv isoforms against MD isoforms to keep only relevant ones
                        if vv_transcript['reference'] == res['name'][1]:
                            transcript_road_signs[res['name'][1]] = {
                                'mane_select': vv_transcript['annotations']['mane_select'],
                                'mane_plus_clinical': vv_transcript['annotations']['mane_plus_clinical'],
                                'refseq_select': vv_transcript['annotations']['refseq_select']
                            }
                # print(transcript_road_signs)
            return render_template(
                'md/gene.html',
                run_mode=md_utilities.get_running_mode(),
                urls=md_utilities.urls,
                gene=gene_name,
                num_iso=num_iso,
                main_iso=main,
                res=result_all,
                annotations=annot,
                max_prot_size=res_size['size'],
                transcript_road_signs=transcript_road_signs
            )
        else:
            close_db()
            return render_template(
                'md/unknown.html',
                run_mode=md_utilities.get_running_mode(),
                query=gene_name
            )
    else:
        close_db()
        return render_template(
            'md/unknown.html',
            run_mode=md_utilities.get_running_mode(),
            query=gene_name
        )

# -------------------------------------------------------------------
# web app - all genes


@bp.route('/genes')
def genes():
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        "SELECT DISTINCT(name[1]) AS hgnc FROM gene ORDER BY name[1]"
    )
    genes = curs.fetchall()
    if genes:
        close_db()
        return render_template(
            'md/genes.html',
            run_mode=md_utilities.get_running_mode(),
            genes=genes
        )
    else:
        close_db()
        return render_template(
            'md/unknown.html',
            run_mode=md_utilities.get_running_mode()
        )

# -------------------------------------------------------------------
# web app - variants in genes


@bp.route('/vars/<string:gene_name>', methods=['GET', 'POST'])
def vars(gene_name=None):
    if gene_name is None:
        return render_template('md/unknown.html', query='No gene provided')
    elif re.search(r'[^\w-]', gene_name):
        return render_template('md/unknown.html', query=gene_name)
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # error = None
    # main isoform?
    curs.execute(
        "SELECT * FROM gene WHERE name[1] = %s AND canonical = 't'",
        (gene_name,)
    )
    main = curs.fetchone()
    if main is not None:
        curs.execute(
            "SELECT name, variant_creation FROM gene WHERE name[1] = %s",
            (gene_name,)
        )  # get all isoforms
        result_all = curs.fetchall()
        num_iso = len(result_all)
        curs.execute(
            "SELECT *, a.id as vf_id FROM variant_feature a, \
            variant b, mobiuser c WHERE a.id = b.feature_id AND \
            a.creation_user = c.id \
            AND a.gene_name[1] = %s AND \
            b.genome_version = 'hg38'",
            (gene_name,)
        )
        variants = curs.fetchall()
        curs.execute(
            "SELECT MAX(prot_size) as size FROM gene WHERE name[1] = %s",
            (gene_name,)
        )
        res_size = curs.fetchone()
        # if vars_type is not None:
        close_db()
        return render_template(
            'md/vars.html',
            run_mode=md_utilities.get_running_mode(),
            urls=md_utilities.urls,
            gene=gene_name,
            num_iso=num_iso,
            variants=variants,
            gene_info=main,
            res=result_all,
            max_prot_size=res_size['size']
        )
    else:
        close_db()
        return render_template(
            'md/unknown.html',
            run_mode=md_utilities.get_running_mode(),
            query=gene_name
        )


# -------------------------------------------------------------------
# web app - variant


@bp.route('/variant/<int:variant_id>', methods=['GET', 'POST'])
def variant(variant_id=None):
    # kept for backward compatiobility of URLs
    return redirect(url_for('api.variant', variant_id=variant_id, caller='browser'))

# -------------------------------------------------------------------
# web app - search engine


@bp.route('/search_engine', methods=['POST'])
def search_engine():
    # print("--{}--".format(request.form['search']))
    query_engine = request.form['search']
    # query_engine = query_engine.upper()
    error = None
    variant_regexp = md_utilities.regexp['variant']
    variant_regexp_flexible = md_utilities.regexp['variant_flexible']
    amino_acid_regexp = md_utilities.regexp['amino_acid']
    nochr_captured_regexp = md_utilities.regexp['nochr_captured']
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']

    if query_engine is not None and \
            query_engine != '':
        pattern = ''
        query_type = ''
        sql_table = 'variant_feature'
        col_names = 'id, c_name, gene_name, p_name'
        semaph_query = 0
        # deal w/ protein names
        query_engine = re.sub(r'\s', '', query_engine)
        if re.search(r'^last$', query_engine):
            # get variant annotated the last 7 days
            if 'db' not in locals():
                db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                curs.execute(
                    "SELECT a.id, a.c_name, a.p_name, a.gene_name, a.creation_user, a.creation_date, b.username from variant_feature a, mobiuser b \
                    WHERE a.creation_user = b.id AND a.creation_date > CURRENT_DATE - 7 ORDER BY creation_date DESC"
                )
                variants = curs.fetchall()
                return render_template('md/variant_multiple.html', variants=variants)
        match_object = re.search(rf'^([{amino_acid_regexp}]{{1}})(\d+)([{amino_acid_regexp}\*]{{1}})$', query_engine)  # e.g. R34X
        if match_object:
            confusing_genes = ['C1R', 'C8G', 'S100G', 'F11R', 'C1S', 'A2M', 'C1D', 'S100P', 'F2R', 'C8A', 'C4A']
            # list of genes that look like the query
            if query_engine.upper() in confusing_genes:
                sql_table = 'gene'
                query_type = 'name[1]'
                col_names = 'name'
                pattern = query_engine.upper()
            else:
                query_type = 'p_name'
                pattern = md_utilities.one2three_fct(query_engine)
        elif re.search(r'^rs\d+$', query_engine):
            query_type = 'dbsnp_id'
            match_object = re.search(r'^rs(\d+)$', query_engine)
            pattern = match_object.group(1)
        elif re.search(r'^p\..+', query_engine):
            query_type = 'p_name'
            var = md_utilities.clean_var_name(query_engine)
            match_object = re.search(r'^(\w{1})(\d+)([\w\*]{1})$', var)  # e.g. p.R34X
            match_object_inter = re.search(r'^(\w{1})(\d+)([d][ue][pl])', var)  # e.g. p.L34del
            match_object_long = re.search(r'^(\w{1})(\d+_)(\w{1})(\d+.+)$', var)  # e.g. p.R34_E68del
            if match_object or match_object_inter or match_object_long:
                pattern = md_utilities.one2three_fct(var)
            else:
                if re.search('X', var):
                    pattern = re.sub(r'X', 'Ter', var)
                elif re.search(r'\*', var):
                    pattern = re.sub(r'\*', 'Ter', var)
                else:
                    pattern = var
        elif re.search(rf'^{ncbi_transcript_regexp}:c\.{variant_regexp}$', query_engine) or \
                re.search(rf'^{ncbi_transcript_regexp}\([A-Za-z0-9-]+\):c\.{variant_regexp}$', query_engine):  # NM acc_no variant
            # f-strings usage https://stackoverflow.com/questions/6930982/how-to-use-a-variable-inside-a-regular-expression
            # API call
            if 'db' not in locals():
                db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            api_key = md_utilities.get_api_key(g, curs)
            match_obj = re.search(rf'^({ncbi_transcript_regexp})\(*[A-Za-z0-9-]*\)*(:c\.{variant_regexp})$', query_engine)
            if api_key is not None:
                return redirect(url_for('api.api_variant_create', variant_chgvs='{0}{1}'.format(match_obj.group(1), match_obj.group(2)), caller='browser', api_key=api_key), code=307)
        elif re.search(r'^[Nn][Mm]_\d+', query_engine):  # NM acc_no
            sql_table = 'gene'
            query_type = 'name[2]'
            col_names = 'name'
            match_object = re.search(rf'^({ncbi_transcript_regexp})', query_engine)
            pattern = match_object.group(1)
        elif re.search(rf'^[Nn][Cc]_0000\d{{2}}\.\d{{1,2}}:g\.{variant_regexp}$', query_engine):  # strict HGVS genomic
            sql_table = 'variant'
            query_type = 'g_name'
            col_names = 'feature_id'
            db = get_db()
            match_object = re.search(rf'^([Nn][Cc]_0000\d{{2}}\.\d{{1,2}}):g\.({variant_regexp})$', query_engine)
            # res_common = md_utilities.get_common_chr_name(db, match_object.group(1))
            chrom = md_utilities.get_common_chr_name(db, match_object.group(1))[0]
            pattern = match_object.group(2)
            # res_common = md_utilities.get_common_chr_name(db, )
        elif re.search(rf'^[Nn][Cc]_0000\d{{2}}\.\d{{1,2}}:g\.{variant_regexp};[\w-]+$', query_engine):  # strict HGVS genomic + gene (API call)
            # API call
            if 'db' not in locals():
                db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            api_key = md_utilities.get_api_key(g, curs)
            match_obj = re.search(rf'^([Nn][Cc]_0000\d{{2}}\.\d{{1,2}}:g\.{variant_regexp});([\w-]+)$', query_engine)
            if api_key is not None:
                return redirect(url_for('api.api_variant_g_create', variant_ghgvs=match_obj.group(1), gene_hgnc=match_obj.group(2), caller='browser', api_key=api_key), code=307)
        elif re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp}):g\.{variant_regexp_flexible}$', query_engine):  # deal w/ genomic
            sql_table = 'variant'
            query_type = 'g_name'
            col_names = 'feature_id'
            match_object = re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp}):g\.({variant_regexp_flexible})$', query_engine)
            chrom = match_object.group(1)
            pattern = match_object.group(2)
            # if re.search(r'>', pattern):
            #    pattern = pattern.upper()
        elif re.search(r'^g\..+', query_engine):  # g. ng dna vars
            query_type = 'ng_name'
            pattern = md_utilities.clean_var_name(query_engine)
        elif re.search(r'^c\..+', query_engine):  # c. dna vars
            query_type = 'c_name'
            pattern = md_utilities.clean_var_name(query_engine)
        elif re.search(r'^%\d+$', query_engine):  # only numbers: get matching variants (exact position match) - specific query
            match_obj = re.search(r'^%(\d+)$', query_engine)
            pattern = match_obj.group(1)
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                r"SELECT {0} FROM {1} WHERE c_name ~ '^{2}[^\d]' OR c_name ~ '_{2}[^\d]' OR p_name ~ '^{2}[^\d]' OR p_name ~ '_{2}[^\d]'".format(
                    col_names, sql_table, pattern
                )
            )
            semaph_query = 1
        elif re.search(r'^\d{2,}$', query_engine):  # only numbers: get matching variants (partial match, at least 2 numbers) - specific query
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                "SELECT {0} FROM {1} WHERE c_name LIKE '%{2}%' OR p_name LIKE '%{2}%'".format(
                    col_names, sql_table, query_engine
                )
            )
            semaph_query = 1
        elif re.search(r'^[A-Za-z0-9-]+$', query_engine):  # genes
            sql_table = 'gene'
            query_type = 'name[1]'
            col_names = 'name'
            pattern = query_engine
            if not re.search(r'[oO][rR][fF]', pattern):
                pattern = pattern.upper()
            else:
                # from experience the only low case in gene is 'orf'
                pattern = re.sub(r'O', 'o', pattern)
                pattern = re.sub(r'R', 'r', pattern)
                pattern = re.sub(r'F', 'f', pattern)
                pattern = pattern.capitalize()
        else:
            error = 'Sorry I did not understand this query ({}).'.format(query_engine)
            # return render_template('md/unknown.html', query=query_engine, transformed_query=pattern)
        if error is None:
            # print(semaph_query)
            if semaph_query == 0:
                if 'db' not in locals():
                    db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                # sql_query = "SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
                # return render_template('md/search_engine.html', query=text)
                # a little bit of formatting
                if re.search('variant', sql_table) and \
                        re.search('>', pattern):
                    # upper for the end of the variant, lower for genomic chr
                    var_match = re.search(r'^(.*)(\d+)([ACTGactg]>[ACTGactg])$', pattern)
                    if var_match:
                        pattern = var_match.group(1).lower() + var_match.group(2) + var_match.group(3).upper()
                    else:
                        error = 'You submitted a forbidden character in "{}".'.format(pattern)
                        flash(error, 'w3-pale-red')
                        return render_template('md/unknown.html', run_mode=app.config['RUN_MODE'])
                    # print(pattern)
                if pattern == 'g_name':
                    curs.execute(
                        "SELECT {0} FROM {1} WHERE chr = {2} AND {3} = '{4}'".format(
                            col_names, sql_table, chrom, query_type, pattern
                        )
                    )
                else:
                    curs.execute(
                        "SELECT {0} FROM {1} WHERE {2} = '{3}'".format(
                            col_names, sql_table, query_type, pattern
                        )
                    )
                result = None
            if sql_table == 'gene':
                result = curs.fetchone()
                if result is None:
                    query_type = 'second_name'
                    # https://www.postgresql.org/docs/9.3/functions-matching.html#POSIX-ESCAPE-SEQUENCES
                    curs.execute(
                        "SELECT {0} FROM {1} WHERE {2} ~* '\m[;,]?{3}[;,]?\M'".format(
                            col_names, sql_table, query_type, pattern
                        )
                    )
                    result_second = curs.fetchone()
                    if result_second is None:
                        close_db()
                        error = 'Sorry the gene does not seem to exist yet in MD or cannot be annotated for some reason ({}).'.format(query_engine)
                    else:
                        return redirect(url_for('md.gene', gene_name=result_second[col_names][0]))
                else:
                    return redirect(url_for('md.gene', gene_name=result[col_names][0]))
            else:
                result = curs.fetchall()
                if not result:
                    if query_type == 'dbsnp_id':
                        # api call to create variant from rs id
                        api_key = md_utilities.get_api_key(g, curs)
                        if api_key is not None:
                            close_db()
                            return redirect(url_for('api.api_variant_create_rs', rs_id='rs{}'.format(pattern), caller='browser', api_key=api_key), code=307)
                    error = 'Sorry the variant or gene does not seem to exist yet in MD or cannot be annotated for some reason ({}).<br /> \
                            You can annotate it directly at the corresponding gene page.'.format(query_engine)
                else:
                    close_db()
                    if len(result) == 1:
                        return redirect(url_for('api.variant', variant_id=result[0][0], caller='browser'))
                    else:
                        return render_template('md/variant_multiple.html', run_mode=md_utilities.get_running_mode(), variants=result)
    else:
        error = 'Please type something for the search engine to work.'
    flash(error, 'w3-pale-red')
    return render_template('md/unknown.html', run_mode=md_utilities.get_running_mode())
