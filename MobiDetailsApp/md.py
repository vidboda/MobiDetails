import re
import os.path
# import time
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
http = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs=certifi.where()
)
# -------------------------------------------------------------------
# web app - index


@bp.route('/')
def index():
    # check vv
    md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.check_vv_instance'))
    vv_instance = json.loads(
                    http.request(
                        'GET',
                        md_api_url,
                        headers=md_utilities.api_agent
                    ).data.decode('utf-8')
                )
    return render_template(
        'md/index.html',
        run_mode=md_utilities.get_running_mode(),
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


@bp.route('/gene/<string:gene_symbol>', methods=['GET', 'POST'])
def gene(gene_symbol=None):
    if gene_symbol is None:
        return render_template('md/unknown.html', query='No gene provided')
    gene_match_obj = re.search(r'^([\w-]+)$', gene_symbol)
    if not gene_match_obj:
        return render_template('md/unknown.html', query=gene_symbol)
    gene_symbol = gene_match_obj.group(1)
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # main isoform? now canonical is stored in db
    curs.execute(
        """
        SELECT *
        FROM gene
        WHERE gene_symbol = %s
            AND canonical = 't'
        """,
        (gene_symbol,)
    )
    main = curs.fetchone()
    if main:
        curs.execute(
            """
            SELECT *
            FROM gene
            WHERE gene_symbol = %s
            ORDER BY number_of_exons DESC
            """,
            (gene_symbol,)
        )  # get all isoforms
        result_all = curs.fetchall()
        num_iso = len(result_all)
        # get metadome json?
        enst_ver = {}
        header = md_utilities.api_agent
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
                            metad_ts = json.loads(
                                        http.request(
                                            'GET',
                                            '{0}get_transcripts/{1}'.format(
                                                md_utilities.urls['metadome_api'],
                                                gene['gene_symbol']
                                            ),
                                            headers=header
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
                                    """
                                    <p>MetaDome first block code failed for gene {0} ({1})<br /> - from {2} with args: {3}</p>
                                    """.format(
                                        gene_symbol,
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
                                            enst_ver[enst]
                                        ),
                                        headers=header
                                    ).data.decode('utf-8')
                                )
                except Exception as e:
                    md_utilities.send_error_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails API error',
                            """
                            <p>MetaDome second block code failed for gene {0} ({1})<br /> - from {2} with args: {3}</p>
                            """.format(
                                gene_symbol,
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
                            # header = md_utilities.api_agent
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
                                    """
                                    <p>Error with metadome submission for {0} ({1})<br /> - from {2} with args: {3}</p>
                                    """.format(
                                        gene_symbol,
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
                                                ),
                                                headers=md_utilities.api_agent
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
                                    """
                                    <p>Error with metadome file writing for {0} ({1})<br /> - from {2} with args: {3}</p>
                                    """.format(
                                        gene_symbol,
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
                """
                SELECT *
                FROM gene_annotation
                WHERE gene_symbol = %s
                """,
                (gene_symbol,)
            )
            annot = curs.fetchone()
            if annot is None:
                annot = {'nognomad': 'No values in gnomAD'}
            curs.execute(
                """
                SELECT MAX(prot_size) AS size
                FROM gene
                WHERE gene_symbol = %s
                """,
                (gene_symbol,)
            )
            res_size = curs.fetchone()
            curs.execute(
                """
                SELECT *
                FROM gene
                WHERE gene_symbol = %s
                ORDER BY number_of_exons DESC
                """,
                (gene_symbol,)
            )  # get all isoforms
            result_all = curs.fetchall()
            num_iso = len(result_all)
            # get refseq select, mane, etc from vv json file
            transcript_road_signs = md_utilities.get_transcript_road_signs(gene_symbol, result_all)
            if not 'error' in transcript_road_signs:            
                clingen_criteria_specification_id = md_utilities.get_clingen_criteria_specification_id(gene_symbol)
                # get isoforms with precomputed spliceAI
                transcript_file_basename = '{0}transcripts/{1}'.format(
                    md_utilities.local_files['spliceai_folder']['abs_path'],
                    main['refseq']
                )
                if not os.path.exists(
                            '{0}.bedGraph.gz'.format(transcript_file_basename)
                        ) or os.path.getctime(
                            '{0}.bedGraph.gz'.format(transcript_file_basename)
                        ) < 1671580800:
                    # if bedgraph created before 20221221 - first online release
                    # check whether we have pre-computed trancript
                    ncbi_chr = md_utilities.get_ncbi_chr_name(db, 'chr{0}'.format(main['chr']), 'hg38')
                    start_g, end_g = md_utilities.get_genomic_transcript_positions_from_vv_json(main['gene_symbol'], main['refseq'], ncbi_chr['ncbi_name'], main['strand'])
                    # header1 = 'browser position chr{0}:{1}-{2}\n'.format(main['chr'], start_g - 1, end_g)
                    header = 'track name="spliceAI_{0}" type=bedGraph description="spliceAI predictions for {0}     acceptor_sites = positive_values       donor_sites = negative_values" visibility=full windowingFunction=maximum color=200,100,0 altColor=0,100,200 priority=20 autoScale=off viewLimits=-1:1 darkerLabels=on\n'.format(main['refseq'])
                    if os.path.exists(
                        '{0}.txt.gz'.format(transcript_file_basename)
                    ):
                        md_utilities.build_compress_bedgraph_from_raw_spliceai(main['chr'], header, transcript_file_basename)
                    else:
                        spliceai_strand = 'plus' if main['strand'] == '+' else 'minus'
                        position_file_basename = '{0}positions/{1}_{2}_{3}_{4}'.format(
                            md_utilities.local_files['spliceai_folder']['abs_path'],
                            'chr{0}'.format(main['chr']),
                            start_g,
                            end_g,
                            spliceai_strand
                        )
                        if os.path.exists(
                            '{0}.txt.gz'.format(position_file_basename)
                        ):
                            md_utilities.build_compress_bedgraph_from_raw_spliceai(main['chr'], header, position_file_basename, transcript_file_basename)
                # get oncoKB gene data
                oncokb_info = md_utilities.get_oncokb_genes_info(gene_symbol)
                close_db()
                return render_template(
                    'md/gene.html',
                    run_mode=md_utilities.get_running_mode(),
                    urls=md_utilities.urls,
                    gene_symbol=gene_symbol,
                    num_iso=num_iso,
                    main_iso=main,
                    res=result_all,
                    annotations=annot,
                    max_prot_size=res_size['size'],
                    clingen_criteria_specification_id=clingen_criteria_specification_id,
                    transcript_road_signs=transcript_road_signs,
                    oncokb_info=oncokb_info
                )
            else:
                close_db()
                return render_template(
                    'md/unknown.html',
                    run_mode=md_utilities.get_running_mode(),
                    query=gene_symbol
                )
        else:
            close_db()
            return render_template(
                'md/unknown.html',
                run_mode=md_utilities.get_running_mode(),
                query=gene_symbol
            )
    else:
        close_db()
        return render_template(
            'md/unknown.html',
            run_mode=md_utilities.get_running_mode(),
            query=gene_symbol
        )

# -------------------------------------------------------------------
# web app - all genes


@bp.route('/genes')
def genes():
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        """
        SELECT DISTINCT(gene_symbol)
        FROM gene
        ORDER BY gene_symbol
        """
    )
    genes = curs.fetchall()
    close_db()
    if genes:
        return render_template(
            'md/genes.html',
            run_mode=md_utilities.get_running_mode(),
            genes=genes
        )
    else:
        return render_template(
            'md/unknown.html',
            run_mode=md_utilities.get_running_mode()
        )

# -------------------------------------------------------------------
# web app - variants in genes


@bp.route('/vars/<string:gene_symbol>', methods=['GET', 'POST'])
def vars(gene_symbol=None):
    if gene_symbol is None:
        return render_template('md/unknown.html', query='No gene provided')
    gene_match_obj = re.search(r'^([\w-]+)$', gene_symbol)
    if not gene_match_obj:
        return render_template('md/unknown.html', query=gene_symbol)
    gene_symbol = gene_match_obj.group(1)
    # gene_symbol = re.escape(gene_symbol)
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # error = None
    # main isoform?
    curs.execute(
        """
        SELECT *
        FROM gene
        WHERE gene_symbol = %s
            AND canonical = 't'
        """,
        (gene_symbol,)
    )
    main = curs.fetchone()
    if main is not None:
        curs.execute(
            """
            SELECT gene_symbol, refseq, variant_creation
            FROM gene
            WHERE gene_symbol = %s
            ORDER BY number_of_exons DESC
            """,
            (gene_symbol,)
        )  # get all isoforms
        result_all = curs.fetchall()
        num_iso = len(result_all)
        transcript_road_signs = md_utilities.get_transcript_road_signs(gene_symbol, result_all)
 
        curs.execute(
            """
            SELECT d.variant_creation, d.refseq, a.c_name, a.p_name, a.start_segment_type, a.start_segment_number, a.creation_date, c.username, a.prot_type, a.ivs_name, a.id as vf_id
            FROM variant_feature a, mobiuser c, gene d
            WHERE a.gene_symbol = d.gene_symbol
                AND a.refseq = d.refseq
                AND a.creation_user = c.id
                AND a.gene_symbol = %s
            """,
            (gene_symbol,)
        )
        variants = curs.fetchall()
        curs.execute(
            """
            SELECT MAX(prot_size) AS size
            FROM gene
            WHERE gene_symbol = %s
            """,
            (gene_symbol,)
        )
        res_size = curs.fetchone()
        # if vars_type is not None:
        close_db()
        clingen_criteria_specification_id = md_utilities.get_clingen_criteria_specification_id(gene_symbol)
        # get oncoKB gene data
        oncokb_info = md_utilities.get_oncokb_genes_info(gene_symbol)
        return render_template(
            'md/vars.html',
            run_mode=md_utilities.get_running_mode(),
            urls=md_utilities.urls,
            gene_symbol=gene_symbol,
            num_iso=num_iso,
            variants=variants,
            gene_info=main,
            res=result_all,
            max_prot_size=res_size['size'],
            clingen_criteria_specification_id=clingen_criteria_specification_id,
            oncokb_info=oncokb_info,
            transcript_road_signs=transcript_road_signs
        )
    else:
        close_db()
        return render_template(
            'md/unknown.html',
            run_mode=md_utilities.get_running_mode(),
            query=gene_symbol
        )


# -------------------------------------------------------------------
# web app - variant


@bp.route('/variant/<int:variant_id>', methods=['GET', 'POST'])
def variant(variant_id=None):
    # kept for backward compatibility of URLs
    return redirect(url_for('api.variant', variant_id=variant_id, caller='browser'))

# -------------------------------------------------------------------
# web app - search engine


@bp.route('/search_engine', methods=['POST'])
def search_engine():
    # print("--{}--".format(request.form['search']))
    # query_engine = md_utilities.get_post_param(request, 'search') 
    query_engine = request.form['search']
    # query_engine = query_engine.upper()
    error = None
    variant_regexp = md_utilities.regexp['variant']
    variant_regexp_flexible = md_utilities.regexp['variant_flexible']
    amino_acid_regexp = md_utilities.regexp['amino_acid']
    nochr_captured_regexp = md_utilities.regexp['nochr_captured']
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    vcf_str_regexp = md_utilities.regexp['vcf_str']

    if query_engine is not None and \
            query_engine != '':
        pattern = ''
        query_type = ''
        sql_table = 'variant_feature'
        col_names = 'id, c_name, gene_symbol, refseq, p_name'
        semaph_query = 0
        query_engine = re.sub(r'\s', '', query_engine)
        query_engine = re.sub(r"'", '', query_engine)
        if re.search(r'^last$', query_engine):
            # get variant annotated the last 7 days
            if 'db' not in locals():
                db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                curs.execute(
                    """
                    SELECT a.id, a.c_name, a.p_name, a.gene_symbol, a.refseq, a.creation_user, a.creation_date, b.username
                    FROM variant_feature a, mobiuser b
                    WHERE a.creation_user = b.id
                        AND a.creation_date > CURRENT_DATE - 7
                    ORDER BY creation_date DESC
                    """
                )
                variants = curs.fetchall()
                close_db()
                return render_template('md/variant_multiple.html', variants=variants)
        match_object = re.search(rf'^([Gg]*[rR]*[hHcC][gGhH][13][978])[:_-]({vcf_str_regexp})$', query_engine)
        if match_object:
            genome_version = md_utilities.translate_genome_version(match_object.group(1))
            if genome_version != 'wrong_genome_input':
                if 'db' in locals():
                    close_db()
                return redirect(
                    url_for(
                        'api.api_create_vcf_str',
                        genome_version=genome_version,
                        vcf_str=match_object.group(2),
                        caller='browser',
                    ),
                    code=307
                )
            else:
                error = 'Your genome version looks suspicious ({}). Supported are hg19, hg38, GRCh37, GRCh38'.format(match_object.group(1))
        else:
            match_object = re.search(rf'^{vcf_str_regexp}$', query_engine)
            if match_object:
                if 'db' in locals():
                    close_db()
                return redirect(
                    url_for(
                        'api.api_create_vcf_str',
                        vcf_str=query_engine,
                        caller='browser',
                    ),
                    code=307
                )
        match_object = re.search(rf'^([{amino_acid_regexp}]{{1}})(\d+)([{amino_acid_regexp}\*]{{1}})$', query_engine)  # e.g. R34X
        if match_object:
            confusing_genes = ['C1R', 'C8G', 'S100G', 'F11R', 'C1S', 'A2M', 'C1D', 'S100P', 'F2R', 'C8A', 'C4A']
            # list of genes that look like the query
            if query_engine.upper() in confusing_genes:
                sql_table = 'gene'
                query_type = 'gene_symbol'
                col_names = 'gene_symbol'
                pattern = query_engine.upper()
            else:
                query_type = 'p_name'
                pattern = md_utilities.one2three_fct(query_engine)
        elif re.search(r'^rs\d+$', query_engine):
            query_type = 'dbsnp_id'
            match_object = re.search(r'^rs(\d+)$', query_engine)
            pattern = match_object.group(1)
        elif re.search(r'^[pP]\..+', query_engine):
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
        elif re.search(rf'^{ncbi_transcript_regexp}:[cC]\.{variant_regexp_flexible}$', query_engine) or \
                re.search(rf'^{ncbi_transcript_regexp}\([A-Za-z0-9-]+\):[cC]\.{variant_regexp_flexible}$', query_engine):  # NM acc_no variant
            match_obj = re.search(rf'^({ncbi_transcript_regexp})\(*[A-Za-z0-9-]*\)*:([cC]\.{variant_regexp_flexible})$', query_engine)
            if 'db' in locals():
                close_db()
            return redirect(
                url_for(
                    'api.api_variant_create',
                    variant_chgvs='{0}:c.{1}'.format(match_obj.group(1), md_utilities.clean_var_name(match_obj.group(2))),
                    caller='browser',
                ),
                code=307
            )
        elif re.search(r'^[Nn][Mm]_\d+', query_engine):  # NM acc_no
            sql_table = 'gene'
            query_type = 'refseq'
            col_names = 'gene_symbol'
            match_object = re.search(r'^(^[Nn][Mm]_\d+)', query_engine)
            if match_object:
                col_names = 'partial_name'
                pattern = match_object.group(1)
        elif re.search(rf'^[Nn][Cc]_0000\d{{2}}\.\d{{1,2}}:[gG]\.{variant_regexp_flexible}$', query_engine):  # strict HGVS genomic
            sql_table = 'variant'
            query_type = 'g_name'
            col_names = 'feature_id'
            if 'db' not in locals():
                db = get_db()
            match_object = re.search(rf'^([Nn][Cc]_0000\d{{2}}\.\d{{1,2}}):([gG]\.{variant_regexp_flexible})$', query_engine)
            # res_common = md_utilities.get_common_chr_name(db, match_object.group(1))
            chrom = md_utilities.get_common_chr_name(db, match_object.group(1))[0]
            pattern = md_utilities.clean_var_name(match_object.group(2))
            if 'db' in locals():
                close_db()
            # res_common = md_utilities.get_common_chr_name(db, )
        elif re.search(rf'^[Nn][Cc]_0000\d{{2}}\.\d{{1,2}}:[gG]\.{variant_regexp};[\w-]+$', query_engine):  # strict HGVS genomic + gene (API call)
            # API call
            match_obj = re.search(rf'^([Nn][Cc]_0000\d{{2}}\.\d{{1,2}}):([gG]\.{variant_regexp});([\w-]+)$', query_engine)
            if 'db' in locals():
                close_db()
            return redirect(
                url_for(
                    'api.api_variant_g_create',
                    variant_ghgvs='{0}:g.{1}'.format(match_obj.group(1), md_utilities.clean_var_name(match_obj.group(2))),
                    gene_hgnc=match_obj.group(3),
                    caller='browser',
                ),
                code=307
            )
        elif re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp}):[gG]\.{variant_regexp_flexible}$', query_engine):  # deal w/ genomic
            sql_table = 'variant'
            query_type = 'g_name'
            col_names = 'feature_id'
            match_object = re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp}):[gG]\.({variant_regexp_flexible})$', query_engine)
            chrom = match_object.group(1)
            pattern = match_object.group(2)
        elif re.search(r'^[gG]\..+', query_engine):  # g. ng dna vars
            query_type = 'ng_name'
            pattern = md_utilities.clean_var_name(query_engine)
        elif re.search(r'^[cC]\..+', query_engine):  # c. dna vars
            query_type = 'c_name'
            print(md_utilities.clean_var_name(query_engine))
            pattern = md_utilities.clean_var_name(query_engine)
        elif re.search(r'^%\d+$', query_engine):  # only numbers: get matching variants (exact position match) - specific query
            match_obj = re.search(r'^%(\d+)$', query_engine)
            pattern = match_obj.group(1)
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                r"""
                SELECT {0}
                FROM {1}
                WHERE c_name ~ '^{2}[^\d]'
                    OR c_name ~ '_{2}[^\d]'
                    OR p_name ~ '^{2}[^\d]'
                    OR p_name ~ '_{2}[^\d]'
                """.format(
                    col_names, sql_table, pattern
                )
            )
            semaph_query = 1
            if 'db' in locals():
                close_db()
        elif re.search(r'^\d{2,}$', query_engine):  # only numbers: get matching variants (partial match, at least 2 numbers) - specific query
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT {0}
                FROM {1}
                WHERE c_name LIKE '%{2}%'
                    OR p_name LIKE '%{2}%'
                """.format(
                    col_names, sql_table, query_engine
                )
            )
            semaph_query = 1
            if 'db' in locals():
                close_db()
        elif re.search(r'^[A-Za-z0-9-]+$', query_engine):  # genes
            sql_table = 'gene'
            query_type = 'gene_symbol'
            col_names = 'gene_symbol'
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
                        if 'db' in locals():
                            close_db()
                        error = 'You submitted a forbidden character in "{}".'.format(pattern)
                        flash(error, 'w3-pale-red')
                        return render_template('md/unknown.html', run_mode=app.config['RUN_MODE'])
                    # print(pattern)
                if pattern == 'g_name':
                    curs.execute(
                        """
                        SELECT {0}
                        FROM {1}
                        WHERE chr = {2}
                            AND {3} = '{4}'
                        """.format(
                            col_names, sql_table, chrom, query_type, pattern
                        )
                    )
                else:
                    if col_names == 'partial_name':
                        col_names = 'gene_symbol'
                        curs.execute(
                            """
                            SELECT {0}
                            FROM {1}
                            WHERE {2} LIKE '{3}%'
                            """.format(
                                col_names, sql_table, query_type, pattern
                            )
                        )
                    else:
                        curs.execute(
                            """
                            SELECT {0}
                            FROM {1}
                            WHERE {2} = '{3}'
                            """.format(
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
                        r"""
                        SELECT {0}
                        FROM {1}
                        WHERE {2} ~* '\m[;,]?{3}[;,]?\M'
                        """.format(
                            col_names, sql_table, query_type, pattern
                        )
                    )
                    result_second = curs.fetchone()
                    if 'db' in locals():
                        close_db()
                    if result_second is None:
                        error = """
                        Sorry the gene does not seem to exist yet in MD or cannot be annotated for some reason ({}).
                        """.format(query_engine)
                    else:
                        return redirect(url_for('md.gene', gene_symbol=result_second[col_names]))
                else:
                    if 'db' in locals():
                        close_db()
                    return redirect(url_for('md.gene', gene_symbol=result[col_names]))
            else:
                result = curs.fetchall()
                if not result:
                    if query_type == 'dbsnp_id':
                        # api call to create variant from rs id
                        if 'db' in locals():
                            close_db()
                        return redirect(
                            url_for(
                                'api.api_variant_create_rs',
                                rs_id='rs{}'.format(pattern),
                                caller='browser',
                                # api_key=api_key
                            ),
                            code=307
                        )
                    error = """
                    Sorry the variant or gene does not seem to exist yet in MD or cannot be annotated for some reason ({}).<br />
                    You can annotate it directly at the corresponding gene page.
                    """.format(query_engine)
                else:
                    if len(result) == 1:
                        if 'db' in locals():
                            close_db()
                        return redirect(url_for('api.variant', variant_id=result[0][0], caller='browser'))
                    else:
                        variants = result
                        if query_type == 'g_name':
                            # coming from a query type: NC_000001.11:g.216422237G>A
                            id_tuple = []
                            for feature_id in result:
                                id_tuple.append(feature_id['feature_id'])
                            curs.execute(
                                """
                                SELECT id, c_name, p_name, gene_symbol, refseq
                                FROM variant_feature
                                WHERE id IN %s
                                ORDER BY id
                                """,
                                (tuple(id_tuple),)
                            )
                            variants = curs.fetchall()
                        if 'db' in locals():
                            close_db()
                        return render_template('md/variant_multiple.html', run_mode=md_utilities.get_running_mode(), variants=variants)
            if 'db' in locals():
                close_db()
    else:
        error = 'Please type something for the search engine to work.'
    flash(error, 'w3-pale-red')
    return render_template('md/unknown.html', run_mode=md_utilities.get_running_mode())


@bp.route('/test_igv', methods=['GET'])
def test_igv():
    return render_template('md/test_igv.html')