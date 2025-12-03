import os
import re
from flask import (
    Blueprint, flash, g, render_template, request, url_for, current_app as app
)
from markupsafe import escape
# from werkzeug.urls import url_parse
# from urllib.parse import urlparse
from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db, close_db
from . import md_utilities

import psycopg2
import psycopg2.extras
import json
import urllib3
import certifi
import bgzip
import requests
import datetime
import twobitreader
# import gzip

bp = Blueprint('ajax', __name__)

# creates a poolmanager
http = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs=certifi.where()
)

# removes content-encoding HTTP header
# https://github.com/igvteam/igv.js/issues/1654


# @bp.after_request
# def remove_header(response):
#     # if response.status_code == 206:
#     del response.headers['content-encoding']
#     del response.headers['content-disposition']
#     return response


######################################################################
# web app - ajax for litvar2

def is_litvar_valid(data):
    """
    Checks if the provided data meets the specified conditions to be considered a valid litvar value.

    Parameters:
    - data (dict): The data to be verified.

    Returns:
    - bool: True if the data meets all conditions, False otherwise.
    """
    if data is None or not data:
        return False
    
    if 'detail' in data and re.search('Variant not found', data["detail"]):
        return False
    return True


@bp.route('/litvar2', methods=['POST'])
def litvar2():
    match_rsid = re.search(r'^(rs\d+)$', request.form['rsid'])
    if match_rsid:
        rsid = match_rsid.group(1)
        header = md_utilities.api_agent
        litvar_data = None
        litvar_url = "{0}{1}%23%23/publications".format(
            md_utilities.urls['ncbi_litvar_apiv2'], rsid
        )
        try:
            litvar_data = json.loads(
                http.request(
                    'GET',
                    escape(litvar_url),
                    headers=header
                ).data.decode('utf-8')
            )
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    '<p>Litvar2 API call failed in {0} with args: {1}</p>'
                    .format(
                        os.path.basename(__file__), e.args
                    )
                ),
                '[MobiDetails - API Error]'
            )
            return """
                <div class="w3-margin w3-panel w3-pale-red w3-leftbar w3-display-container">
                    <p><strong>The Litvar2 query failed</strong> - <i>Please reload and if the problem persist <a href="" onmouseover="this.href='mailto:{}'" onmouseout="this.href=''">contact our administrator</a>.</i></p>
                </div>""".format(app.config["MAIL_USERNAME"])
        if is_litvar_valid(litvar_data):
            pubmed_info = dict()

            togows_url = '{0}/entry/ncbi-pubmed/'.format(
                md_utilities.urls['togows']
            )

            pubmed_count = litvar_data['pmids_count']
            for pubmed_id in litvar_data['pmids'][:400]:
                togows_url = '{0}{1},'.format(togows_url, pubmed_id)
            togows_url = '{0}.json'.format(togows_url[:-1])
            
            try:
                # using togows to get details on publications
                pubmeds = json.loads(
                    http.request(
                        'GET',
                        togows_url,
                        headers=header
                    ).data.decode('utf-8')
                )
                for article in pubmeds:
                    if 'authors' in article and \
                            len(article['authors']) > 0:
                        pmid = int(article['pmid'])
                        pubmed_info[pmid] = {
                            'title': article['title'],
                            'journal': article['journal'],
                            'year': article['year'],
                            'author': article['authors'][0]
                        }
            except Exception:
                for pubmed_id in litvar_data['pmids']:
                    pmid = int(pubmed_id)
                    pubmed_info[pmid] = {'title': ''}
            if not pubmed_info:
                for pubmed_id in litvar_data['pmids']:
                    pmid = int(pubmed_id)
                    pubmed_info[pmid] = {'title': ''}
            # get litvar direct link of rsid
            litvar_sensor_url = "{0}{1}".format(
                md_utilities.urls['ncbi_litvar_apiv2_sensor'], rsid
            )
            try:
                litvar_sensor = json.loads(
                    http.request(
                        'GET',
                        escape(litvar_sensor_url),
                        headers=header
                    ).data.decode('utf-8')
                )
            except Exception as e:
                # litvar_sesnor is not mandatory
                pass
            litvar_link = None
            if 'rsid' in litvar_sensor and \
                    litvar_sensor['rsid'] == rsid and \
                    'link' in litvar_sensor:
                litvar_link = litvar_sensor['link']
            return render_template(
                'ajax/litvar.html',
                urls=md_utilities.urls,
                pmids=pubmed_info,
                pubmed_count=pubmed_count,
                rsid=rsid,
                litvar_link=litvar_link
            )
    return """
        <div class="w3-margin w3-panel w3-pale-yellow w3-leftbar w3-display-container">
            <p>Currently no match in PubMed using LitVar2 API</p>
        </div>"""
######################################################################
# web app - ajax for defgen export file


@bp.route('/defgen', methods=['POST'])
def defgen():
    genome_regexp = md_utilities.regexp['genome']
    match_genome = re.search(
        rf'^({genome_regexp})$',
        request.form['genome']
    )
    match_varid = re.search(r'^(\d+)$', request.form['vfid'])
    if match_varid and \
            match_genome:
        variant_id = match_varid.group(1)
        # genome = request.form['genome']
        genome = match_genome.group(1)
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # get all variant_features and gene info
        curs.execute(
            """
            SELECT *
            FROM variant_feature a, variant b, gene c
            WHERE a.id = b.feature_id
                AND a.gene_symbol = c.gene_symbol
                AND a.refseq = c.refseq AND a.id = %s
                AND b.genome_version = %s
            """,
            (variant_id, genome)
        )
        vf = curs.fetchone()
        if vf:
            file_content = "GENE;VARIANT;A_ENREGISTRER;ETAT;RESULTAT;VARIANT_P;\
VARIANT_C;ENST;NM;POSITION_GENOMIQUE;CLASSESUR5;CLASSESUR3;COSMIC;RS;\
REFERENCES;CONSEQUENCES;COMMENTAIRE;CHROMOSOME;GENOME_REFERENCE;\
NOMENCLATURE_HGVS;LOCALISATION;SEQUENCE_REF;LOCUS;ALLELE1;ALLELE2\r\n"
            rsid = ''
            if vf['dbsnp_id']:
                rsid = 'rs{0}'.format(vf['dbsnp_id'])
            file_content += "{0};{1}:c.{2};;;;p.{3};c.{2};{4};{1};{5};\
;;;{6};;{7};;chr{8};{9};chr{8}:g.{10};{11} {12};;;;\r\n".format(
                vf['gene_symbol'], vf['refseq'],
                vf['c_name'], vf['p_name'], vf['enst'], vf['pos'],
                rsid, vf['prot_type'], vf['chr'], genome,
                vf['g_name'], vf['start_segment_type'], vf['start_segment_number']
            )
        else:
             # intergenic variant
            curs.execute(
                """
                SELECT *
                FROM variant_feature a, variant b
                WHERE a.id = b.feature_id
                    AND a.id = %s
                    AND b.genome_version = %s
                """,
                (variant_id, genome)
            )
            vf = curs.fetchone()
            file_content = "GENE;VARIANT;A_ENREGISTRER;ETAT;RESULTAT;VARIANT_P;\
VARIANT_C;ENST;NM;POSITION_GENOMIQUE;CLASSESUR5;CLASSESUR3;COSMIC;RS;REFERENCES;\
CONSEQUENCES;COMMENTAIRE;CHROMOSOME;GENOME_REFERENCE;NOMENCLATURE_HGVS;LOCALISATION;\
SEQUENCE_REF;LOCUS;ALLELE1;ALLELE2\r\n"
            rsid = ''
            if vf['dbsnp_id']:
                rsid = 'rs{0}'.format(vf['dbsnp_id'])
#             file_content += ";;;;;;;;;{0};;;;{1};;;;\
# chr{2};{3};chr{2}:g.{4};;;;;\r\n".format(
#                 vf['pos'], rsid, vf['chr'], genome,
#                 vf['g_name']
#             )
            file_content += "intergenic;;;;;;{0}:chr{1}:g.{2};;intergenic;{3};;;;{4};;;;\
chr{1};{3};chr{1}:g.{2};;;;;\r\n".format(
                genome, vf['chr'], vf['g_name'],
                vf['pos'], rsid
            )
        # print(file_content)
        app_path = os.path.dirname(os.path.realpath(__file__))
        file_loc = "defgen/{0}-{1}-{2}{3}-{4}.csv".format(
            genome, vf['chr'], vf['pos'], vf['pos_ref'], vf['pos_alt']
        )
        with open("{0}/static/{1}".format(app_path, file_loc), "w") as defgen_file:
            defgen_file.write(file_content)
        close_db()
        variant = "chr{0}:g.{1}".format(
                vf['chr'], vf['g_name']
            )
        if vf['c_name']:
            variant = "{0}:c.{1}".format(
                vf['refseq'], vf['c_name']
            )
        return render_template(
            'ajax/defgen.html',
            variant=variant,
            defgen_file=file_loc,
            genome=genome
        )
    else:
        # close_db()
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails Ajax error',
                '<p>DefGen file generation failed in {} (no variant_id)</p>'
                .format(
                    os.path.basename(__file__)
                )
            ),
            '[MobiDetails - Ajax Error]'
        )
        return """
            <div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">
                Impossible to create DEFGEN file
            </div>
        """

# -------------------------------------------------------------------
# web app - ajax for intervar API


@bp.route('/intervar', methods=['POST'])
def intervar():
    genome_regexp = md_utilities.regexp['genome']
    match_genome = re.search(rf'^({genome_regexp})$', request.form['genome'])
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    match_nochr_chrom = re.search(rf'^({nochr_chrom_regexp})$', request.form['chrom'])
    match_pos = re.search(r'^(\d+)$', request.form['pos'])
    match_ref = re.search(r'^([ATGC]+)$', request.form['ref'])
    match_alt = re.search(r'^([ATGC]+)$', request.form['alt'])
    gene_symbol_regexp = md_utilities.regexp['gene_symbol']
    match_gene_symbol = re.search(rf'^({gene_symbol_regexp})$', request.form['gene'])
    if match_genome and \
            match_nochr_chrom and \
            match_pos and \
            match_ref and \
            match_alt and \
            match_gene_symbol:
        genome = match_genome.group(1)
        chrom = match_nochr_chrom.group(1)
        pos = match_pos.group(1)
        ref = match_ref.group(1)
        alt = match_alt.group(1)
        gene = match_gene_symbol.group(1)
        header = md_utilities.api_agent
        if len(ref) > 1 or len(alt) > 1:
            return 'No wintervar for indels'
        if ref == alt:
            return '{0} reference is equal to variant: no wIntervar query'.format(genome)
        intervar_url = "{0}{1}&chr={2}&pos={3}&ref={4}&alt={5}".format(
            md_utilities.urls['intervar_api'], genome, chrom,
            pos, ref, alt
        )
        # print(intervar_url)
        try:
            # intervar_http = urllib3.PoolManager(cert_reqs='CERT_NONE')
            # urllib3.disable_warnings()
            # above used when there was a n issue with intervar certificate
            intervar_data = [
                json.loads(
                    http.request(
                        'GET',
                        intervar_url,
                        headers=header
                    ).data.decode('utf-8')
                )
            ]
        except Exception:
            try:
                # intervar can return multiple json objects, e.g.:
                # {"Intervar":"Uncertain significance","Chromosome":1,
                # "Position_hg19":151141512,"Ref_allele":"T","Alt_allele":"A"
                # ,"Gene":"SCNM1","PVS1":0,"PS1":0,"PS2":0,"PS3":0,"PS4":0,
                # "PM1":1,"PM2":1,"PM3":0,"PM4":0,"PM5":0,"PM6":0,"PP1":0,
                # "PP2":0,"PP3":0,"PP4":0,"PP5":0,"BA1":0,"BP1":0,"BP2":0,
                # "BP3":0,"BP4":0,"BP5":0,"BP6":0,"BP7":0,"BS1":0,"BS2":0,
                # "BS3":0,"BS4":0}{"Intervar":"Uncertain significance",
                # "Chromosome":1,"Position_hg19":151141512,"Ref_allele":"T",
                # "Alt_allele":"A","Gene":"TNFAIP8L2-SCNM1","PVS1":0,"PS1":0,
                # "PS2":0,"PS3":0,"PS4":0,"PM1":1,"PM2":1,"PM3":0,"PM4":0,
                # "PM5":0,"PM6":0,"PP1":0,"PP2":0,"PP3":0,"PP4":0,"PP5":0,
                # "BA1":0,"BP1":0,"BP2":0,"BP3":0,"BP4":0,"BP5":0,"BP6":0,
                # "BP7":0,"BS1":0,"BS2":0,"BS3":0,"BS4":0}
                intervar_list = re.split(
                    '}{',
                    http.request(
                        'GET',
                        intervar_url,
                        headers=header
                    ).data.decode('utf-8')
                )
                i = 0
                for obj in intervar_list:
                    # some housekeeping to get proper strings
                    obj = obj.replace('{', '').replace('}', '')
                    obj = '{{{}}}'.format(obj)
                    intervar_list[i] = obj
                    i += 1
                intervar_data = []
                for obj in intervar_list:
                    # print(obj)
                    intervar_data.append(json.loads(obj))
            except Exception as e:
                md_utilities.send_error_email(
                    md_utilities.prepare_email_html(
                        'MobiDetails API error',
                        """
                        <p>Intervar API call failed for {0}-{1}-{2}-{3}-{4}- url: {5} <br /> - from {6} with args: {7}</p>
                        """.format(
                            genome, chrom, pos, ref, alt,
                            intervar_url, os.path.basename(__file__), e.args
                        )
                    ),
                    '[MobiDetails - API Error]'
                )
                return "<span>No wintervar class</span>"
        intervar_acmg = None
        intervar_criteria = ''
        # print(md_utilities.acmg_criteria['PVS1'])
        if len(intervar_data) == 1:
            try:
                intervar_acmg = intervar_data[0]['Intervar']
                for key in intervar_data[0]:
                    if key != 'Chromosome' and \
                            intervar_data[0][key] == 1:
                        intervar_criteria = """
                        {0}&nbsp;<div
                            class="w3-col {1} w3-opacity-min w3-hover-shadow"
                            style="width:50px;"
                            onmouseover="$(\'#acmg_info\').text(\'{2}: {3}\');">
                        {2}</div>
                        """.format(
                            str(intervar_criteria),
                            md_utilities.get_acmg_criterion_color(key),
                            key,
                            md_utilities.acmg_criteria[key]
                        )
            except Exception:
                return "<span>wintervar looks down</span>"
        else:
            for intervar_dict in intervar_data:
                # intervar likely returns several json objects
                if intervar_dict['Gene'] == gene:
                    intervar_acmg = intervar_dict['Intervar']
                    for key in intervar_dict:
                        if key != 'Chromosome' and \
                                intervar_dict[key] == 1:
                            intervar_criteria = """
                            {0}&nbsp;
                            <div
                                class="w3-col {1} w3-opacity-min w3-hover-shadow"
                                style="width:50px;"
                                onmouseover="$(\'#acmg_info\').text(\'{2}: {3}\');">
                            {2}</div>
                            """.format(
                                str(intervar_criteria),
                                md_utilities.get_acmg_criterion_color(key),
                                key,
                                md_utilities.acmg_criteria[key]
                            )
        if intervar_acmg is not None:
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT html_code
                FROM valid_class
                WHERE acmg_translation = %s
                """,
                (intervar_acmg.lower(),)
            )
            res = curs.fetchone()
            close_db()
            return """
            <span style='color:{0};'>{1}</span>
            <span> with the following criteria:</span><br /><br />
            <div class='w3-row-padding w3-center'>{2}</div><br />
            <div id='acmg_info'></div>
            """.format(
                res['html_code'],
                intervar_acmg,
                intervar_criteria
            )
        else:
            return "<span>No wintervar class</span>"
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails API error',
                """
                <p>GeneBe API call failed for from {0} with args: A mandatory argument is missing: {1}</p>
                """.format(
                    os.path.basename(__file__),
                    request.form
                )
            ),
            '[MobiDetails - API Error]'
        )
        return "<span>Bad request</span>"


# -------------------------------------------------------------------
# web app - ajax for genebe

@bp.route('/genebe', methods=['POST'])
def genebe():
    # https://api.genebe.net/cloud/api-public/v1/variant?chr=6&pos=108561712&ref=C&alt=T&transcript=NM_001455.4&gene_symbol=FOXO3&useRefseq=True&useEnsembl=False&omitAcmg=False&omitCsq=False&omitBasic=True&omitAdvanced=True&omitNormalization=True&genome=hg38
    # api key
    # curl -X 'GET' -u YOUR_EMAIL:YOUR_API_KEY \
    # 'https://api.genebe.net/cloud/api-public/v1/variant?chr=6&pos=160585140&ref=T&alt=G&genome=hg38' \
    # -H 'Accept: application/json'
    # https://genebe.net/about/api
    # Use Basic Authorization with your email as the username and the API key as the password in your API requests.
    # headers = urllib3.make_headers(basic_auth='abc:xyz')
    # r = http.request('GET', url, headers=headers)
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    gene_symbol_regexp = md_utilities.regexp['gene_symbol']
    genome_regexp = md_utilities.regexp['genome']
    match_genome = re.search(rf'^({genome_regexp})$', request.form['genome'])
    match_nochr_chrom = re.search(rf'^({nochr_chrom_regexp})$', request.form['chrom'])
    match_pos = re.search(r'^(\d+)$', request.form['pos'])
    match_ref = re.search(r'^([ATGC]+)$', request.form['ref'])
    match_alt = re.search(r'^([ATGC]+)$', request.form['alt'])
    ncbi_transcript_match = re.search(rf'^({ncbi_transcript_regexp})$', request.form['ncbi_transcript'])
    match_gene_symbol = re.search(rf'^({gene_symbol_regexp})$', request.form['gene'])
    if match_genome and \
            match_nochr_chrom and \
            match_pos and \
            match_ref and \
            match_alt and \
            ncbi_transcript_match and \
            match_gene_symbol:
        genome = match_genome.group(1)
        chrom = match_nochr_chrom.group(1)
        pos = match_pos.group(1)
        ref = match_ref.group(1)
        alt = match_alt.group(1)
        ncbi_transcript = ncbi_transcript_match.group(1)
        gene = match_gene_symbol.group(1)
        headers = urllib3.make_headers(basic_auth='{0}:{1}'.format(app.config["GENEBE_EMAIL"], app.config["GENEBE_API_KEY"]))
        if ref == alt:
            return '{0} reference is equal to variant: no GeneBe query'.format(genome)
        genebe_url = "{0}/cloud/api-public/v1/variant?&chr={1}&pos={2}&ref={3}&alt={4}&transcript={5}&gene_symbol={6}&useRefseq=True&useEnsembl=False&omitAcmg=False&omitCsq=False&omitBasic=False&omitAdvanced=False&omitNormalization=True&genome={7}".format(
            md_utilities.urls['genebe_api'],
            chrom, pos, ref, alt,
            ncbi_transcript, gene, genome
        )
        # print(headers)
        try:
            genebe_data = [
                json.loads(
                    http.request(
                        'GET',
                        genebe_url,
                        headers=headers
                    ).data.decode('utf-8')
                )
            ]
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    """
                    <p>GeneBe API call failed for {0}-{1}-{2}-{3}-{4}- url: {5} <br /> - from {6} with args: {7}</p>
                    """.format(
                        genome, chrom, pos, ref, alt,
                        genebe_url, os.path.basename(__file__), e.args
                    )
                ),
                '[MobiDetails - API Error]'
            )
            return "<span>MD failed to query genebe.net</span>"
        try:
            genebe_acmg = genebe_data[0]['variants'][0]['acmg_classification']
            genebe_acmg_score = genebe_data[0]['variants'][0]['acmg_score']
            if genebe_acmg_score != 0:
                genebe_criteria = genebe_data[0]['variants'][0]['acmg_criteria']
        except Exception as e:
            # print(genebe_data)
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    """
                    <p>AMCG class not retrieved in GeneBe object: {0}<br /> from {1} </p>
                    """.format(
                        genebe_data, genebe_url
                    )
                ),
                '[MobiDetails - API Error]'
            )
            return "<span>GeneBe returned no classification for this variant or MD was unable to interpret it.</span>"
        # print(genebe_data)
        html_criteria = ''
        if genebe_acmg_score != 0:
            criteria_list = re.split(',', genebe_criteria)
            for criterion in criteria_list:
                strict_criterion = criterion
                criterion_modulation = ''
                width = 50
                criterion_obj = re.search('^([BP][MVSP]S?\d)_(Supporting|Moderate|Strong|Very_Strong)$', criterion)
                if criterion_obj:
                    width = 150
                    strict_criterion = criterion_obj.group(1)
                    criterion_modulation = criterion_obj.group(2)
                if strict_criterion == criterion:
                    # e.e. PP3 alone need to determine default modulation
                    if criterion == 'PVS1':
                        criterion_modulation = 'Very_Strong'
                    elif re.match('[BP]S', criterion):
                        criterion_modulation = 'Strong'
                    elif re.match('PM', criterion):
                        criterion_modulation = 'Moderate'
                    elif re.match('[BP]P', criterion):
                        criterion_modulation = 'Supporting'
                html_criteria = """
                    {0}&nbsp;<div
                        class="w3-col {1} w3-opacity-min w3-hover-shadow"
                        style="width:{2}px;"
                        onmouseover="$(\'#genebe_acmg_info\').text(\'{3}: {4}\');">
                    {3}</div>
                    """.format(
                        str(html_criteria),
                        md_utilities.get_genebe_acmg_criterion_color(strict_criterion, criterion_modulation),
                        width,
                        criterion,
                        md_utilities.acmg_criteria[strict_criterion]
                    )
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        genebe_acmg_txt = genebe_acmg
        if re.search('_', genebe_acmg):
            genebe_acmg_txt = genebe_acmg.replace('_', ' ')
        curs.execute(
            """
            SELECT html_code
            FROM valid_class
            WHERE acmg_translation = %s
            """,
            (genebe_acmg_txt.lower(),)
        )
        res = curs.fetchone()
        close_db()
        if genebe_acmg_score != 0:
            return """
            <span style='color:{0};'>{1}</span>
            <span> with the following criteria:</span><br /><br />
            <div class='w3-row-padding w3-center'>{2}</div><br />
            <div id='genebe_acmg_info'></div>
            """.format(
                res['html_code'],
                genebe_acmg_txt,
                html_criteria
            )
        else:
            return """
            <span style='color:{0};'>{1}</span>
            <span> as no criterion could be applied</span>
            """.format(
                res['html_code'],
                genebe_acmg_txt
            )
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails API error',
                """
                <p>GeneBe API call failed from {0} with args: A mandatory argument is missing: {1}</p>
                """.format(
                    os.path.basename(__file__),
                    request.form
                )
            ),
            '[MobiDetails - API Error]'
        )
        return "<span>Bad request</span>"


# -------------------------------------------------------------------
# web app - ajax for spliceaivisual


@bp.route('/spliceaivisual', methods=['POST'])
def spliceaivisual():
    # check and get params
    chrom = pos = ref = alt = ncbi_transcript = strand = variant_id = None
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    chr_match = re.search(rf'^({nochr_chrom_regexp})$', request.form['chrom'])
    pos_match = re.search(r'^(\d+)$', request.form['pos'])
    ref_match = re.search(r'^([ATGCatgc]+)$', request.form['ref'])
    alt_match = re.search(r'^([ATGCatgc]+)$', request.form['alt'])
    ncbi_transcript_match = re.search(rf'^({ncbi_transcript_regexp})$', request.form['ncbi_transcript'])
    strand_match = re.search(r'^([\+-])$', request.form['strand'])
    variant_id_match = re.search(r'^(\d+)$', request.form['variant_id'])
    gene_symbol_match = re.search(r'^([\w\.-]+)$', request.form['gene_symbol'])
    caller_match = re.search(r'(spliceaivisual_full_button|automatic)', request.form['caller'])
    if chr_match and \
            pos_match and \
            ref_match and \
            alt_match and \
            ncbi_transcript_match and \
            strand_match and \
            variant_id_match and \
            gene_symbol_match and \
            caller_match:
        chrom = chr_match.group(1)
        pos = pos_match.group(1)
        ref = ref_match.group(1).upper()
        alt = alt_match.group(1).upper()
        ncbi_transcript = ncbi_transcript_match.group(1)
        strand = strand_match.group(1)
        variant_id = variant_id_match.group(1)
        gene_symbol = gene_symbol_match.group(1)
        caller = caller_match.group(1)
        # build file basename
        transcript_file_basename = '{0}transcripts/{1}'.format(
            md_utilities.local_files['spliceai_folder']['abs_path'],
            ncbi_transcript
        )
        # headers for bedgraph file
        # header1 = 'browser position chr{0}:{1}-{2}\n'.format(chrom, int(pos) - 1, pos)
        header = 'track name="spliceAI_{0}" type=bedGraph description="spliceAI predictions for {0}     acceptor_sites = positive_values       donor_sites = negative_values" visibility=full windowingFunction=maximum color=200,100,0 altColor=0,100,200 priority=20 autoScale=off viewLimits=-1:1 darkerLabels=on\n'.format(ncbi_transcript)
        db = get_db()
        ncbi_chr = md_utilities.get_ncbi_chr_name(db, 'chr{0}'.format(chrom), 'hg38')
        start_g, end_g = md_utilities.get_genomic_transcript_positions_from_vv_json(gene_symbol, ncbi_transcript, ncbi_chr['ncbi_name'], strand)
        # start_g, end_g = 1-based
        if caller == 'automatic':
            # caller = automatic or spliceaivisual_full_button
            # if automatic we need to get the WT transcript
            # spliceaivisual_full_button => we send the complete mutant transcript to spliceai
            # do we have the wt bedgraph
            if os.path.exists(
                '{0}.bedGraph.gz'.format(transcript_file_basename)
            ):
                response = 'ok'
            elif os.path.exists(
                '{0}.txt.gz'.format(transcript_file_basename)
            ):
                # build new bedgraph.gz from .txt.gz
                response = md_utilities.build_compress_bedgraph_from_raw_spliceai(chrom, header, transcript_file_basename)
                
            else:
                # check whether we have pre-computed chr-start-end-strand
                # we need ncbi chr
                # db = get_db()
                # ncbi_chr = md_utilities.get_ncbi_chr_name(db, 'chr{0}'.format(chrom), 'hg38')
                # start_g, end_g = md_utilities.get_genomic_transcript_positions_from_vv_json(gene_symbol, ncbi_transcript, ncbi_chr['ncbi_name'], strand)
                # print('gene: {0}, transcript: {1}, chr: {2}, strand: {3}, start: {4}, end: {5}'.format(gene_symbol, ncbi_transcript, ncbi_chr['ncbi_name'], strand, start_g, end_g))
                spliceai_strand = 'plus' if strand == '+' else 'minus'

                position_file_basename = '{0}positions/{1}_{2}_{3}_{4}'.format(
                    md_utilities.local_files['spliceai_folder']['abs_path'],
                    'chr{0}'.format(chrom),
                    start_g,
                    end_g,
                    spliceai_strand
                )
                if os.path.exists(
                    '{0}.txt.gz'.format(position_file_basename)
                ):
                    # build new bedgraph.gz from .txt.gz
                    response = md_utilities.build_compress_bedgraph_from_raw_spliceai(chrom, header, position_file_basename, transcript_file_basename)
                else:
                    # build new bedgraph from scratch ? How many cases?
                    # response = 'ok'
                    # currently return error
                    return '<p style="color:red">SpliceAI-visual is currently not available for this transcript.</p>'
        # files paths
        variant_file_basename = '{0}/variants/'.format(
            md_utilities.local_files['spliceai_folder']['abs_path'],
        )
        variant_file = '{0}{1}.bedGraph.gz'.format(
            variant_file_basename,
            variant_id
        )
        full_variant_file = '{0}{1}_full_transcript.bedGraph.gz'.format(
            variant_file_basename,
            variant_id
        )
        # bed file for inserted nucleotides track
        # create bed file for inserted nucleotides if necessaery
        bed_ins_file_basename = '{0}variants/{1}_ins.bed'.format(
            md_utilities.local_files['spliceai_folder']['abs_path'],
            variant_id
        )
        if not os.path.exists(bed_ins_file_basename):
            with open(
                bed_ins_file_basename,
                'w'
            ) as bed_ins_file:
                if len(ref) != len(alt) and \
                        ref[0:1] != alt[0:1]:
                    # complex deletions / insertions (indels) - general case
                    # not needed if len(ref) == len(alt)
                    start_ins = int(pos) - 1 if strand == '+' else int(pos) + len(ref) - len(alt) - 1
                    bed_ins_file.write('{0}\t{1}\t{2}\n'.format(chrom, int(start_ins), int(start_ins) + len(alt)))
                elif len(alt) > len(ref) and \
                        len(ref) == 1:
                    # insertions, duplications
                    start_ins = pos if strand == '+' else int(pos) - len(alt) + 1
                    bed_ins_file.write('{0}\t{1}\t{2}\n'.format(chrom, int(start_ins), int(start_ins) + len(alt) - 1))
                else:
                    bed_ins_file.write('{0}\t{1}\t{2}\n'.format(chrom, 1, 1))
        # files caches
        if caller == 'automatic' and \
                os.path.exists(variant_file):
            response = 'ok'
            if os.path.exists(full_variant_file):
                response = 'full'
            return response
        # get mutant spliceai predictions
        header2 = 'track name="ALT allele (MobiDetails ID: {0})" type=bedGraph description="spliceAI predictions for variant {0} in MobiDetails    acceptor_sites = positive_values       donor_sites = negative_values" visibility=full windowingFunction=maximum color=200,100,0 altColor=0,100,200 priority=20 autoScale=off viewLimits=-1:1 darkerLabels=on\n'.format(variant_id)
        # build mt sequence
        # we cannot add intergenic sequence (to be replaced with NNNs)
        offset = 10000
        # 0-based
        genome = twobitreader.TwoBitFile(
            '{}.2bit'.format(md_utilities.local_files['human_genome_hg38']['abs_path'])
        )
        current_chrom = genome['chr{}'.format(chrom)]
        variant_type = 'substitution'
        extreme_positions = []
        if len(ref) == 1 and \
                len(alt) == 1:
            # substitutions
            if caller == 'automatic':
                extreme_positions.append(int(pos) - offset - 1)
                extreme_positions.append(int(pos) + offset)
                mt_seq = current_chrom[extreme_positions[0]:int(pos) - 1].upper() + alt + current_chrom[int(pos):extreme_positions[1]].upper()
            else:
                mt_seq = current_chrom[start_g - 1:int(pos) - 1].upper() + alt + current_chrom[int(pos):end_g - 1].upper()
        elif ((len(ref) > 1 and
                len(alt) > 1) or
                (ref[0:1] != alt[0:1])):
            # complex deletions / insertions - indels pos ref and alt differ contrary to simple insertiosn or deletions
            variant_type = 'indel'
            if caller == 'automatic':
                extreme_positions.append(int(pos) - offset - 1)
                extreme_positions.append(int(pos) + offset + len(alt) - 1)
                mt_seq = current_chrom[extreme_positions[0]:int(pos) - 1].upper() + alt + current_chrom[int(pos) + len(ref) -1:extreme_positions[1]].upper()
            else:
                mt_seq = current_chrom[start_g - 1:int(pos) - 1].upper() + alt + current_chrom[int(pos) + len(ref) - 1:end_g].upper()
        elif len(ref) > len(alt) and \
                len(alt) == 1:
            # deletions
            # start differs as: TGGCGGCGGC-T => pos remains ref contrary to subs and indels
            variant_type = 'deletion'
            if caller == 'automatic':
                extreme_positions.append(int(pos) - offset)
                extreme_positions.append(int(pos) + offset + len(ref) - 1)
                mt_seq = current_chrom[extreme_positions[0]:int(pos)].upper() + current_chrom[int(pos) + len(ref) - 1:extreme_positions[1]].upper()
            else:
                mt_seq = current_chrom[start_g:int(pos)].upper() + current_chrom[int(pos) + len(ref) - 1:end_g].upper()
        elif len(alt) > len(ref) and \
                len(ref) == 1:
            # insertions / duplications
            # start differs as: T-TGGC => pos remains ref contrary to subs and indels
            variant_type = 'insertion'
            if caller == 'automatic':
                extreme_positions.append(int(pos) - offset)
                extreme_positions.append(int(pos) + offset + len(alt) - 1)
                mt_seq = current_chrom[extreme_positions[0]:int(pos) - 1].upper() + alt + current_chrom[int(pos):extreme_positions[1]].upper()
            else:
                mt_seq = current_chrom[start_g:int(pos) - 1].upper() + alt + current_chrom[int(pos):end_g].upper()
        else:
            mt_seq = None
        if caller == 'automatic' and \
                mt_seq:
            # ok replace putative intergenic sequences with NNNs
            if extreme_positions[0] < start_g and \
                    start_g > 0:
                # we are in an intergenic region
                # ------------<exon 1>----
                # ATCGACATCGACATCGGCTCGCTC
                # should become
                # NNNNNNNNNNNNATCGGCTCGCTC
                nt2remove_pos = start_g - extreme_positions[0]
                tmp_list = list(mt_seq)
                for i in range(nt2remove_pos):
                    tmp_list[i] = 'N'
                mt_seq = "".join(tmp_list)
            if extreme_positions[1] > end_g and \
                    end_g > 0:
                # we are in an intergenic region
                # ------------<last exon>----
                # ATCGACATCGACATCGGCTCGCTCTAG
                # should become
                # ATCGACATCGACATCGGCTCGCTNNNN
                nt2remove_pos = len(mt_seq) - (extreme_positions[1] - end_g)
                tmp_list = list(mt_seq)
                for i in range(nt2remove_pos, len(mt_seq)):
                    tmp_list[i] = 'N'
                mt_seq = "".join(tmp_list)
        if mt_seq:
            response = None
            if strand == '-':
                mt_seq = md_utilities.reverse_complement(mt_seq)
            # spliceai call
            try:
                # req_results = requests.get(
                #     '{0}/spliceai'.format(md_utilities.urls['spliceai_internal_server']),
                #     json={'mt_seq': mt_seq},
                #     headers=md_utilities.api_agent
                # )
                req_results = requests.post(
                    '{0}/spliceai'.format(md_utilities.urls['spliceai_internal_server']),
                    json={'mt_seq': mt_seq},
                    headers={'Content-Type': 'application/json'}
                )
            except requests.exceptions.ConnectionError:
                return '<p style="color:red">Failed to establish a connection to the SpliceAI-visual server.</p>'
            # 1-based
            if req_results.status_code == 200:
                spliceai_results = json.loads(req_results.content)
                current_mt_file = variant_file if caller == 'automatic' else full_variant_file
                if spliceai_results['spliceai_return_code'] == 0 and \
                        spliceai_results['error'] is None and \
                        not os.path.exists(current_mt_file):
                    # build compressed bedgraph
                    bedgraph_data = header2
                    mt_acceptor_scores = spliceai_results['result']['mt_acceptor_scores']
                    mt_donor_scores = spliceai_results['result']['mt_donor_scores']
                    # 0-based
                    abs_pos = (int(pos) - offset - 1) if caller == 'automatic' else start_g - 1
                    if strand == '-':
                        mt_acceptor_scores = dict(reversed(list(mt_acceptor_scores.items())))
                        mt_donor_scores = dict(reversed(list(mt_donor_scores.items())))
                        abs_pos += 1
                    i = len(mt_acceptor_scores)
                    # print(i)
                    bedgraph_insertion = 'track name="Insertion allele (MobiDetails ID: {0})" type=bedGraph description="spliceAI rediction for inserted nucleotides for variant {0} in MobiDetails    acceptor_sites = positive_values       donor_sites = negative_values" visibility=full windowingFunction=maximum color=200,100,0 altColor=0,100,200 priority=20 autoScale=off viewLimits=-1:1 darkerLabels=on\n'.format(variant_id)
                    for relative_pos in mt_acceptor_scores:
                        rel_pos_genome = relative_pos
                        if strand == '-':
                            rel_pos_genome = len(mt_acceptor_scores) - i
                            i -= 1
                        sai_score = mt_acceptor_scores[relative_pos][1] if float(mt_acceptor_scores[relative_pos][1]) > float(mt_donor_scores[relative_pos][1]) else - float(mt_donor_scores[relative_pos][1])
                        current_pos = abs_pos + int(rel_pos_genome)
                        if variant_type == 'substitution' or \
                                (variant_type == 'indel' and
                                    len(ref) == len(alt)):
                            bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos - 1, current_pos, sai_score)
                        elif variant_type == 'deletion':
                            if current_pos <= int(pos) - 1:
                                bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos, current_pos + 1, sai_score)
                            else:
                                bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos + len(ref) - 1, current_pos + len(ref), sai_score)
                        elif variant_type == 'insertion':
                            if current_pos <= int(pos) - 1:
                                bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos, current_pos + 1, sai_score)
                            elif current_pos >=  int(pos) and \
                                    current_pos <  int(pos) + len(alt) - 1:
                                ins_pos = current_pos if strand == '+' else current_pos - len(alt) + 1
                                bedgraph_insertion = '{0}{1}\t{2}\t{3}\t{4}\n'.format(bedgraph_insertion, chrom, ins_pos, ins_pos + 1, sai_score)
                            else:
                                bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos - len(alt) + 1, current_pos - len(alt) + 2, sai_score)
                        elif variant_type == 'indel':
                            if current_pos <= int(pos) - 1:
                                bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos - 1, current_pos, sai_score)
                            elif current_pos >= int(pos) and \
                                    current_pos < int(pos) + len(alt):
                                ins_pos = current_pos if strand == '+' else current_pos + len(ref) - len(alt)
                                bedgraph_insertion = '{0}{1}\t{2}\t{3}\t{4}\n'.format(bedgraph_insertion, chrom, ins_pos - 1, ins_pos, sai_score)
                            else:
                                if len(ref) >= len(alt):
                                    bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos + (len(ref) - len(alt)) - 1, current_pos + (len(ref) - len(alt)), sai_score)
                                else:
                                    bedgraph_data = bedgraph_data + 'chr{0}\t{1}\t{2}\t{3}\n'.format(chrom, current_pos - (len(alt) - len(ref)) - 1, current_pos - (len(alt) - len(ref)), sai_score)
                    # run bgzip and tabix on file being either mt file or full transcript
                    # write bgzip file
                    md_utilities.bgzip_data_onto_file(bedgraph_data, current_mt_file)
                    # tabix
                    md_utilities.create_tabix_index(current_mt_file)

                    # create bed file for wt and mt if necessaery
                    bed_file_basename = '{0}variants/{1}.bed'.format(
                        md_utilities.local_files['spliceai_folder']['abs_path'],
                        variant_id
                    )
                    if not os.path.exists(bed_file_basename):
                        with open(
                            bed_file_basename,
                            'w'
                        ) as bed_file:
                            if variant_type == 'substitution':
                                bed_file.write('{0}\t{1}\t{2}\n'.format(chrom, int(pos) - 1, pos))
                            elif variant_type == 'deletion':
                                bed_file.write('{0}\t{1}\t{2}\n'.format(chrom, int(pos), int(pos) + len(ref) - 1))
                            elif variant_type == 'insertion':
                                bed_file.write('{0}\t{1}\t{2}\n'.format(chrom, int(pos) - 1, int(pos) + 1))
                            if variant_type == 'indel':
                                bed_file.write('{0}\t{1}\t{2}\n'.format(chrom, int(pos) - 1, int(pos) + len(ref) - 1))
                    bedgraph_ins_file_basename = '{0}variants/{1}_ins.bedGraph.gz'.format(
                        md_utilities.local_files['spliceai_folder']['abs_path'],
                        variant_id
                    )
                    # create bedgraph file for inserted nucleotides if necessary
                    if not os.path.exists(bedgraph_ins_file_basename):
                        # uncompressed version
                        # with open(
                        #     bedgraph_ins_file_basename,
                        #     'w'
                        # ) as bedgraph_ins_file:
                        #     bedgraph_ins_file.write(bedgraph_insertion)
                        # compressed version
                        # run bgzip and tabix on bedgraph_ins_file_basename
                        # write bgzip file
                        md_utilities.bgzip_data_onto_file(bedgraph_insertion, bedgraph_ins_file_basename)
                        # tabix
                        md_utilities.create_tabix_index(bedgraph_ins_file_basename)
                    response = 'ok'
                if caller == 'automatic' and \
                        os.path.exists(full_variant_file):
                    response = 'full'
                if spliceai_results['spliceai_return_code'] != 0 or \
                        spliceai_results['error']:
                    print(spliceai_results)
                    return '<p style="color:red">Bad params for SpliceAI-visual.</p>'
            else:
                print(req_results.content)
                return '<p style="color:red">Bad params for SpliceAI-visual.</p>'
            if not response:
                response = 'ok'
            return response
        else:
            return '<p style="color:red">Bad params for SpliceAI-visual.</p>'
    else:
        return '<p style="color:red">Bad params for SpliceAI-visual.</p>'


# -------------------------------------------------------------------
# web app - ajax for LOVD API


@bp.route('/lovd', methods=['POST'])
def lovd():
    genome = chrom = g_name = c_name = gene = None
    genome_regexp = md_utilities.regexp['genome']
    match_genome = re.search(rf'^({genome_regexp})$', request.form['genome'])
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    match_nochr_chrom = re.search(rf'^({nochr_chrom_regexp})$', request.form['chrom'])
    variant_regexp = md_utilities.regexp['variant']
    match_g_name = re.search(rf'^({variant_regexp})$', request.form['g_name'])
    match_c_name = re.search(rf'^(c\.{variant_regexp})$', request.form['c_name'])
    gene_symbol_regexp = md_utilities.regexp['gene_symbol']
    match_gene_symbol = re.search(rf'^({gene_symbol_regexp})$', request.form['gene'])
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    match_ncbi_transcript = re.search(rf'^({ncbi_transcript_regexp})$', request.form['ncbi_transcript'])
    # print(request.form)
    if match_genome and \
            match_nochr_chrom and \
            match_g_name and \
            match_c_name and \
            match_gene_symbol and \
            match_ncbi_transcript:
        genome = match_genome.group(1)
        chrom = match_nochr_chrom.group(1)
        g_name = match_g_name.group(1)
        c_name = match_c_name.group(1)
        gene = match_gene_symbol.group(1)
        refseq = match_ncbi_transcript.group(1)
        # for r. nomenclature
        rna_hgvs = ''
        protein_hgvs = ''
        header = md_utilities.api_agent
        # pos_19 = request.form['pos']
        if re.search(r'=', g_name):
            # TODO switch genome and retest
            return md_utilities.lovd_error_html(
                "Genomic reference is equal to variant: no LOVD query"
            )
            # return 'hg19 reference is equal to variant: no LOVD query'
        positions = md_utilities.compute_start_end_pos(g_name)
        # http://www.lovd.nl/search.php?
        # build=hg19&position=chr$evs_chr:".$evs_pos_start."_".$evs_pos_end
        lovd_url = "{0}search.php?build={1}&position=chr{2}:{3}_{4}".format(
            md_utilities.urls['lovd'],
            genome,
            chrom,
            positions[0],
            positions[1]
        )
        # print(lovd_url)
        lovd_data = None
        try:
            lovd_data = re.split(
                '\n',
                http.request(
                    'GET',
                    lovd_url,
                    headers=header
                ).data.decode('utf-8')
            )
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    '<p>LOVD API call failed in {0} with args: {1}</p>'.format(
                        os.path.basename(__file__), e.args
                    )
                ),
                '[MobiDetails - API Error]'
            )
        # print(lovd_url)
        # print(http.request('GET', lovd_url).data.decode('utf-8'))
        if lovd_data is not None:
            lovd_effect_count = None
            if len(lovd_data) == 1:
                return md_utilities.lovd_error_html(
                    "No match in LOVD public instances"
                )
            lovd_data.remove('"hg_build"\t"g_position"\t"gene_id"\t\"nm_accession"\t"DNA"\t"url"')
            lovd_urls = []
            i = 1
            html = ''
            html_list = []
            for candidate in lovd_data:
                fields = re.split('\t', candidate)
                # check if the variant is the same than ours
                # print(fields)
                if len(fields) > 1:
                    fields[4] = fields[4].replace('"', '')
                    if fields[4] == c_name or re.match(escape(c_name), fields[4]):
                        lovd_urls.append(fields[5])
                        continue
                    # for SNVs, if there is a discrepancy between NM versions (e.g. NM_020778.4 and NM_020778.5), c-nmae can be completely different
                    # then we can allow a match in genomic position (from query) and in the substitution, e.g. G>A
                    if re.search(r'>', c_name):
                        csub = md_utilities.get_substitution_nature(c_name)
                        field_sub = md_utilities.get_substitution_nature(fields[4])
                        if csub == field_sub:
                            lovd_urls.append(fields[5])
            if len(lovd_urls) > 0:
                for url in lovd_urls:
                    lovd_name = None
                    url = url.replace('"', '')
                    parsed_url = md_utilities.parse_url(url)
                    # print(parsed_url)
                    lovd_base_url = 'https://{0}{1}'.format(
                        parsed_url[1],
                        parsed_url[2]
                    )
                    # print(lovd_base_url)
                    # lovd_base_url = 'https://{0}{1}'.format(
                    #     url_parse(url).host,
                    #     url_parse(url).path
                    # )
                    match_obj = re.search(
                        r'^(.+\/)variants\.php$',
                        lovd_base_url
                    )
                    if match_obj:
                        lovd_base_url = match_obj.group(1)
                        try:
                            lovd_fh = open(
                                md_utilities.
                                local_files['lovd_ref']['abs_path']
                            )
                            for line in lovd_fh:
                                if re.search(
                                    r'{}'.format(lovd_base_url),
                                    line
                                ):
                                    lovd_name = line.split('\t')[0]
                        except Exception:
                            # finding the lovd file is not mandatory
                            pass
                    html_li = '<li>'
                    html_li_end = '</li>'
                    if len(lovd_urls) == 1:
                        html_li = ''
                        html_li_end = ''
                    if lovd_name is not None:
                        html_list.append(
                            "{0}<a href='{1}' target='_blank'>{2} </a>{3}"
                            .format(html_li, url, lovd_name, html_li_end)
                        )
                    else:
                        html_list.append(
                            "{0}<a href='{1}' target='_blank'>Link {2} </a>{3}"
                            .format(html_li, url, i, html_li_end)
                        )
                    i += 1
                # get LOVD effects e.g.
                # https://databases.lovd.nl/shared/api/rest/variants/USH2A?search_position=g.216420460&show_variant_effect=1&format=application/json
                # if positions[0] == positions[1]:
                #     lovd_api_url = '{0}{1}?search_position=g.{2}&show_variant_effect=1&format=application/json'.format(
                #         md_utilities.urls['lovd_api_variants'], gene, positions[0]
                #     )
                # else:
                lovd_api_url = '{0}{1}?search_position=g.{2}_{3}&show_variant_effect=1&format=application/json'.format(
                    md_utilities.urls['lovd_api_variants'], gene, positions[0], positions[1]
                )
                lovd_effect = None
                try:
                    lovd_effect = json.loads(
                        http.request(
                            'GET',
                            lovd_api_url,
                            headers=header
                        ).data.decode('utf-8')
                    )
                except Exception:
                    # if lovd api does not answer, pass
                    pass
                if lovd_effect is not None and \
                        len(lovd_effect) != 0:
                    # print(lovd_effect)
                    lovd_effect_count = {
                        'effect_reported': {},
                        'effect_concluded': {}
                    }
                    for var in lovd_effect:
                        if var['owned_by'][0] == 'MobiDetails' and \
                                len(lovd_urls) == 1:
                            return md_utilities.lovd_error_html(
                                """
                                No match in LOVD public instances except a MobiDetails\' previous submission to \
                                <a href={} target='_blank'>GV LOVD Shared</a>
                                """.format(lovd_urls[0])
                            )
                        # check here whether we are looking at the correct variant
                        nm, nm_ver = md_utilities.decompose_transcript(refseq)
                        # get rid of version !beware may lead to errors
                        lovd_transcript = refseq
                        if 'variants_on_transcripts' in var:
                            for transcript in var['variants_on_transcripts']:
                                if re.search(nm, transcript):
                                    lovd_transcript = transcript
                            # for SNVs, if there is a discrepancy between NM versions (e.g. NM_020778.4 and NM_020778.5), c-nmae can be completely different
                            # then we can allow a match in genomic position (from query) and in the substitution, e.g. G>A
                            csub = None
                            field_sub = None
                            if re.search(r'>', c_name):
                                csub = md_utilities.get_substitution_nature(c_name)
                                field_sub = md_utilities.get_substitution_nature(var['variants_on_transcripts'][transcript]['DNA'])
                            if lovd_transcript in var['variants_on_transcripts'] and \
                                    (var['variants_on_transcripts'][lovd_transcript]['DNA'] == c_name \
                                    or re.match(escape(c_name), var['variants_on_transcripts'][transcript]['DNA'])) or \
                                    (csub and field_sub and csub == field_sub): 
                                if var['effect_reported'][0] not in \
                                        lovd_effect_count['effect_reported']:
                                    lovd_effect_count['effect_reported'][var['effect_reported'][0]] = 1
                                else:
                                    lovd_effect_count['effect_reported'][var['effect_reported'][0]] += 1
                                if var['effect_concluded'][0] not in \
                                        lovd_effect_count['effect_concluded']:
                                    lovd_effect_count['effect_concluded'][var['effect_concluded'][0]] = 1
                                else:
                                    lovd_effect_count['effect_concluded'][var['effect_concluded'][0]] += 1
                                # for rna hgvs
                                for transcript in var['variants_on_transcripts']:
                                    if 'RNA' in var['variants_on_transcripts'][transcript] and \
                                            re.search(nm, transcript) and \
                                            var['variants_on_transcripts'][transcript]['RNA'] != rna_hgvs:
                                        new_rna_hgvs = re.escape(var['variants_on_transcripts'][transcript]['RNA'])
                                        # print(new_rna_hgvs)
                                        if 'id' in var and \
                                                not re.search(f'{new_rna_hgvs}', rna_hgvs):
                                            rna_hgvs = '{0} <br />{1}'.format(
                                                '<a href="https://databases.lovd.nl/shared/variants/{0}" title="Check LOVD" target="_blank">{1}</a>'.format(
                                                    var['id'],
                                                    var['variants_on_transcripts'][transcript]['RNA']
                                                ),
                                                rna_hgvs
                                            )
                                            # get also p. https://github.com/vidboda/MobiDetails/issues/92
                                            protein_hgvs = '{0}<br />{1}'.format(var['variants_on_transcripts'][transcript]['protein'], protein_hgvs)
                                        elif not re.search(new_rna_hgvs, rna_hgvs):
                                            rna_hgvs = '{0}, {1}'.format(var['variants_on_transcripts'][transcript]['RNA'], rna_hgvs)
                                            protein_hgvs = '{0}, {1}'.format(var['variants_on_transcripts'][transcript]['protein'], protein_hgvs)
                # print(rna_hgvs)
            else:
                return md_utilities.lovd_error_html(
                    "No match in LOVD public instances"
                )
            html = """            
            <tr>
                <td class="w3-left-align" id="lovd_feature"style="vertical-align:middle;">LOVD Matches:
                    <span id="lovd_rna_hgvs" style="display:none;visibility:hidden;">{0}</span>
                    <span id="lovd_protein_hgvs" style="display:none;visibility:hidden;">{1}</span>
                </td>
                <td class="w3-left-align"><ul>{2}</ul></td>
                <td class="w3-left-align" id="lovd_description" style="vertical-align:middle;">
                    <em class="w3-small">LOVD match in public instances</em>
                </td>
            </tr>
            """.format(rna_hgvs, protein_hgvs, ''.join(html_list))
            # print(html)
            if lovd_effect_count is not None:
                reported_effect_list = []
                concluded_effect_list = []
                for feat in lovd_effect_count:
                    # print(feat)
                    for effect in lovd_effect_count[feat]:
                        # print(effect)
                        if feat == 'effect_reported':
                            reported_effect_list.append("""
                                <div
                                    class="w3-col w3-{0} w3-opacity-min w3-padding w3-margin-top w3-margin-left w3-hover-shadow"
                                    style="width:180px;">
                                {1}: {2}
                                </div>
                                """.format(
                                    md_utilities.lovd_effect[effect]['color'],
                                    md_utilities.lovd_effect[effect]['translation'],
                                    lovd_effect_count[feat][effect]
                                )
                            )
                        else:
                            concluded_effect_list.append("""
                                <div
                                    class="w3-col w3-{0} w3-opacity-min w3-padding w3-margin-top w3-margin-left w3-hover-shadow"
                                    style="width:180px;">
                                {1}: {2}  </div>
                                """.format(
                                    md_utilities.lovd_effect[effect]['color'],
                                    md_utilities.lovd_effect[effect]['translation'],
                                    lovd_effect_count[feat][effect]
                                )
                            )
                html = """
                {0}$<tr>
                <td class="w3-left-align" id="lovd_r_feature" style="vertical-align:middle;">
                    LOVD Effect Reported:
                </td>
                <td class="w3-center" style="vertical-align:middle;">
                    <div class="w3-row w3-center">{1}</div><br />
                </td>
                <td class="w3-left-align" id="lovd_r_feature" style="vertical-align:middle;">
                    <em class="w3-small">Effects reported by LOVD submitters</em>
                </td>
                </tr>,<tr>
                <td class="w3-left-align" id="lovd_c_description" style="vertical-align:middle;">
                    LOVD Effect Concluded:
                </td>
                <td class="w3-center" style="vertical-align:middle;">
                    <div class="w3-row w3-center">{2}</div><br />
                </td>
                <td class="w3-left-align" id="lovd_c_description" style="vertical-align:middle;">
                    <em class="w3-small">Effects concluded by LOVD curators</em></td>
                </tr>
                """.format(html, ''.join(reported_effect_list), ''.join(concluded_effect_list))
                # print(html)
            return html
        else:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    '<p>LOVD service looks down in {}</p>'.format(
                        os.path.basename(__file__)
                    )
                ),
                '[MobiDetails - API Error]'
            )
            return md_utilities.lovd_error_html("LOVD service looks down")
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails API error',
                """
                <p>LOVD API call failed in {0} with args: a mandatory argument is missing for {1}</p>
                """.format(
                    os.path.basename(__file__),
                    request.form['c_name']
                )
            ),
            '[MobiDetails - API Error]'
        )
        return md_utilities.lovd_error_html("LOVD query malformed")

# -------------------------------------------------------------------
# web app - ajax for ACMG classification modification


@bp.route('/modif_class', methods=['POST'])
@login_required
def modif_class():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    # tr_html = 'notok'
    match_variant_id = re.search(r'^(\d+)$', request.form['variant_id'])
    match_acmg_select = re.search(r'^(\d+)$', request.form['acmg_select']) 
    if match_variant_id and \
            match_acmg_select and \
            'acmg_comment' in request.form:
        variant_id = match_variant_id.group(1)
        acmg_select = match_acmg_select.group(1)
        acmg_comment = request.form['acmg_comment']
        today = datetime.datetime.now()
        date = '{0}-{1}-{2}'.format(
            today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
        )

        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # semaphore to know whether it is a first time submission or not
        semaph = 0
        # get all variant_features and gene info
        try:
            curs.execute(
                """
                SELECT class_date
                FROM class_history
                WHERE variant_feature_id = %s
                    AND acmg_class = %s
                    AND mobiuser_id = %s
                """,
                (variant_id, acmg_select, g.user['id'])
            )
            res = curs.fetchone()
            if res:
                if str(res['class_date']) == str(date):
                    # print(("{0}-{1}").format(res['class_date'], date))
                    tr_html = """
                    <tr id='already_classified'>
                        <td>You already classified this variant with the same class today.
                        If you just want to modify comments, remove the previous classification
                        and start from scratch.
                        </td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                    </tr>
                    """
                    close_db()
                    return tr_html
                curs.execute(
                    """
                    UPDATE class_history
                    SET class_date  = %s, comment = %s
                    WHERE variant_feature_id = %s
                        AND acmg_class = %s
                        AND mobiuser_id = %s
                    """,
                    (date, acmg_comment, variant_id, acmg_select, g.user['id'])
                )
            else:
                # if first classification and current owner ==
                # mobidetails => user become owner
                curs.execute(
                    """
                    SELECT acmg_class
                    FROM class_history
                    WHERE variant_feature_id = %s
                    """,
                    (variant_id,)
                )
                res_acmg = curs.fetchone()
                # print("res_amcg: {}".format(res_acmg))
                if not res_acmg:
                    semaph = 1
                    curs.execute(
                        """
                        SELECT creation_user
                        FROM variant_feature
                        WHERE id = %s
                        """,
                        (variant_id,)
                    )
                    res_user = curs.fetchone()
                    # print("res_user_id: {}"
                    # .format(res_user['creation_user']))
                    # get mobidetails user id
                    mobidetails_id = md_utilities.get_user_id(
                        'mobidetails', db
                    )
                    if res_user and \
                            res_user['creation_user'] == mobidetails_id:
                        curs.execute(
                            """
                            UPDATE variant_feature
                            SET creation_user = %s
                            WHERE id = %s
                            """,
                            (g.user['id'], variant_id)
                        )
                curs.execute(
                    """
                    INSERT INTO class_history (variant_feature_id, acmg_class, mobiuser_id, class_date, comment)
                    VALUES (%s, %s, %s, %s, %s )
                    """,
                    (variant_id, acmg_select, g.user['id'], date, acmg_comment)
                )
            db.commit()
            curs.execute(
                """
                SELECT html_code, acmg_translation, lovd_translation
                FROM valid_class
                WHERE acmg_class = %s
                """,
                (acmg_select,)
            )
            acmg_details = curs.fetchone()
            # get HGVS genomic, cDNA, protein HGNC
            # gene symbol and refseq acc version
            genome_version = 'hg19'
            # swith to hg38 if hg38 only
            curs.execute(
                """
                SELECT genome_version
                FROM variant
                WHERE feature_id = %s
                    AND genome_version = %s
                """,
                (variant_id, genome_version)
            )
            res_genome = curs.fetchone()
            if not res_genome:
                genome_version = 'hg38'
            curs.execute(
                """
                SELECT a.c_name, a.gene_symbol, a.refseq, a.p_name, a.dbsnp_id, b.g_name, d.hgnc_id, c.ncbi_name
                FROM variant_feature a, variant b, chromosomes c, gene d
                WHERE a.id = b.feature_id
                    AND b.genome_version = c.genome_version
                    AND b.chr = c.name
                    AND a.gene_symbol = d.gene_symbol
                    AND a.refseq = d.refseq
                    AND a.id = %s AND b.genome_version = %s
                """,
                (variant_id, genome_version)
            )
            res_var = curs.fetchone()
            tr_html = """
            <tr id='{0}-{1}-{2}'>
                <td class='w3-left-align'>{3}(<em>{4}</em>):c.{5}</td>
                <td class='w3-left-align'>{6}</td>
                <td class='w3-left-align'>{7}</td>
                <td class='w3-left-align'>
                    <span style='color:{8};'>Class {1} ({9})</span>
                </td>
                <td>
                    <div class='w3-cell-row'>
                        <span class='w3-container w3-left-align w3-cell'> {10}</span>
                    </div>
                </td>
            </tr>""".format(
                    g.user['id'],
                    escape(acmg_select),
                    escape(variant_id),
                    res_var['refseq'],
                    res_var['gene_symbol'],
                    res_var['c_name'],
                    g.user['username'],
                    date,
                    acmg_details['html_code'],
                    acmg_details['acmg_translation'],
                    escape(acmg_comment)
                )
            # Send data to LOVD if relevant
            # REPLACE md_utilities.host['dev'] with md_utilities.host['prod'] \
            # WHEN LOVD FEATURE IS READY
            if g.user['lovd_export'] is True and \
                    genome_version == 'hg19' and \
                    acmg_select != 7:
                    # risk factor not sent to LOVD for the moment
                with open(
                    md_utilities.local_files['lovd_api_json']['abs_path']
                ) as json_file:
                    lovd_json = json.load(json_file)
                # get HGVS genomic, cDNA, protein HGNC
                # gene symbol and refseq acc version
                lovd_json['lsdb']['variant'][0]['ref_seq']['@accession'] = res_var['ncbi_name']
                lovd_json['lsdb']['variant'][0]['name']['#text'] = 'g.{}'.format(res_var['g_name'])

                if res_var['dbsnp_id']:
                    lovd_json['lsdb']['variant'][0]['db_xref'][0]['@accession'] = 'rs{}'.format(res_var['dbsnp_id'])
                else:
                    lovd_json['lsdb']['variant'][0].pop('db_xref', None)
                if res_var['hgnc_id'] == 0:
                    lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['gene']['@accession'] = res_var['gene_symbol']
                else:
                    lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['gene']['@accession'] = res_var['hgnc_id']
                lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['ref_seq']['@accession'] = res_var['refseq']
                lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['name']['#text'] = 'c.{}'.format(res_var['c_name'])
                lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['seq_changes']['variant'][0]['name']['#text'] = 'p.({})'.format(res_var['p_name'])
                if semaph == 1:
                    # first time submission
                    lovd_json['lsdb']['variant'][0]['pathogenicity']['@term'] = acmg_details['lovd_translation']
                else:
                    # build ACMG class for LOVD update
                    curs.execute(
                        """
                        SELECT acmg_class
                        FROM class_history
                        WHERE variant_feature_id = %s
                        """,
                        (variant_id,)
                    )
                    res_acmg = curs.fetchall()
                    # print(res_acmg)
                    if res_acmg:
                        lovd_json['lsdb']['variant'][0]['pathogenicity']['@term'] = md_utilities.define_lovd_class(res_acmg, db)
                    else:
                        # we should never get in there
                        lovd_json['lsdb']['variant'][0]['pathogenicity']['@term'] = acmg_details['lovd_translation']
                # send request to LOVD API
                # headers
                header = md_utilities.api_agent
                header['Content-Type'] = 'application/json'
                # print (json.dumps(lovd_json))
                try:
                    lovd_response = http.request(
                        'POST',
                        md_utilities.urls['lovd_api_submissions'],
                        body=json.dumps(lovd_json).encode('utf-8'),
                        headers=header
                    ).data.decode('utf-8')
                    print('LOVD submission for {0}:g.{1} : {2}'.format(
                        res_var['ncbi_name'],
                        res_var['g_name'],
                        lovd_response
                    ))
                except Exception:
                    pass
            close_db()
            return tr_html
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Variant class modification failed for variant {0} with args: {1}</p>
                    """.format(variant_id, e.args)
                ),
                '[MobiDetails - MD variant class Error]'
            )
            close_db()
            return md_utilities.danger_panel(
                '',
                """
                Sorry, something went wrong with the addition of
                this annotation. An admin has been warned.
                """)

    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails error',
                '<p>Variant class modification failed for variant \
{0} with args: wrong parameter {0}-{1}</p>'.format(
                    request.form['variant_id'],
                    request.form['acmg_select']
                )
            ),
            '[MobiDetails - MD variant class Error]'
        )
        return md_utilities.danger_panel(
            '',
            """
            Sorry, something went wrong with the addition of
            this annotation. An admin has been warned.
            """)


# -------------------------------------------------------------------
# web app - ajax to remove ACMG classification


@bp.route('/remove_class', methods=['POST'])
@login_required
def remove_class():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    if re.search(r'^\d+$', request.form['variant_id']) and \
            re.search(r'^\d+$', request.form['acmg_class']):
        variant_id = request.form['variant_id']
        acmg_class = request.form['acmg_class']
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            curs.execute(
                """
                DELETE
                FROM class_history
                WHERE variant_feature_id = %s
                    AND acmg_class = %s
                    AND mobiuser_id = %s
                """,
                (variant_id, acmg_class, g.user['id'])
            )
            db.commit()
            return 'ok'
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Variant class deletion failed for {0} with args: {1}</p>
                    """.format(variant_id, e.args)
                ),
                '[MobiDetails - MD variant class Error]'
            )
        close_db()
    return md_utilities.danger_panel(
        '',
        """
        Sorry, something went wrong with the deletion of this annotation. An admin has been warned.
        """)

# -------------------------------------------------------------------
# web app - ajax to contact other users


@bp.route('/send_var_message', methods=['POST'])
@login_required
def send_var_message():
    match_receiver_id = re.search(r'^(\d+)$', request.form['receiver_id'])
    match_message_object = re.search(
                    r'^Object: \[(MobiDetails\s-\sQuery\sfrom.+)\]$',
                    request.form['message_object']
                )
    if match_receiver_id and \
            match_message_object:
        if request.form['message'] != '':
            receiver = {}
            receiver['id'] = match_receiver_id.group(1)
            message = request.form['message']
            message_object = match_message_object.group(1)
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # get username and email
            curs.execute(
                """
                SELECT id, username, email
                FROM mobiuser
                WHERE id = %s
                """,
                (receiver['id'],)
            )
            # res = curs.fetchall()
            receiver = curs.fetchone()
            message.replace("\n", "<br />")
            message += """
            <br /><br />
            <p>You can contact user {0} directly at {1}</p>
            """.format(
                    g.user['username'],
                    g.user['email']
                )
            md_utilities.send_email(
                md_utilities.prepare_email_html(
                    message_object, message, False
                ),
                '[{}]'.format(message_object),
                [receiver['email']]
            )
            close_db()
            return md_utilities.info_panel(
                'Your email has just been sent.',
                '',
                '',
                'w3-pale-green'
            )
        else:
            return md_utilities.danger_panel(
                '',
                'Please complete the message part of the form.'
            )
    md_utilities.send_error_email(
        md_utilities.prepare_email_html(
            'MobiDetails error',
            """
            <p>An email was not sent from {0} to {1}<br />Object was {2}<br />Message was:<br />{3}</p>
            """.format(
                g.user['id'],
                request.form['receiver_id'],
                request.form['message_object'],
                request.form['message']
            )
        ),
        '[MobiDetails - Email Error]'
    )
    return md_utilities.danger_panel(
        '',
        """
        Sorry, something went wrong with this message. An admin has been warned.
        """)

# -------------------------------------------------------------------
# web app - ajax for variant creation via VV API
# https://rest.variantvalidator.org/webservices/variantvalidator.html


@bp.route('/create', methods=['POST'])
def create():
    # This method will have to be merged with /api/variant/create in a future version
    # start_time = time.time()
    header = {'User-Agent': md_utilities.api_agent['User-Agent']}
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )    
    if request.form['new_variant'] == '':
        return md_utilities.danger_panel(
            'variant creation attempt',
            'Please fill in the form before submitting!'
        )
    gene_symbol_regexp = md_utilities.regexp['gene_symbol']
    match_gene = re.search(rf'^({gene_symbol_regexp})$', request.form['gene'])
    refseq_regexp = md_utilities.regexp['ncbi_transcript']
    match_refseq = re.search(rf'^({refseq_regexp})$', request.form['acc_no'])
    variant_regexp = md_utilities.regexp['variant']
    match_variant = re.search(
                rf'^(c\.{variant_regexp})$',
                request.form['new_variant']
            )
    if match_gene and \
            match_refseq and \
            match_variant:
        gene = match_gene.group(1)
        acc_no = match_refseq.group(1)
        new_variant = match_variant.group(1)
        new_variant = new_variant.replace(" ", "").replace("\t", "")
        original_variant = new_variant
        alt_nm = None
        if 'alt_iso' in request.form:
            match_alt_iso = re.search(rf'^({refseq_regexp})$', request.form['alt_iso'])
            if match_alt_iso:
                alt_nm = match_alt_iso.group(1)
            # alt_nm = request.form['alt_iso']
            # if alt_nm != '' and alt_nm != acc_no:
                if alt_nm != acc_no:
                    acc_no = alt_nm
        # variant already registered?
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT id, c_name as nm
            FROM variant_feature
            WHERE c_name = %s
                AND refseq = %s
            """,
            (new_variant.replace("c.", ""), acc_no)
        )
        res = curs.fetchone()
        if res:
            close_db()
            return md_utilities.info_panel(
                'Variant already in MobiDetails: ',
                '{0}:{1}'.format(acc_no, new_variant),
                res['id']
            )

        if re.search(r'c\..+', new_variant):
            # is vv alive?
            vv_base_url = md_utilities.get_vv_api_url()
            # print(vv_base_url)
            # print('--- 2- {} seconds ---'.format((time.time() - start_time)))
            if not vv_base_url:
                close_db()
                return md_utilities.danger_panel(
                        new_variant,
                        """
                        Variant Validator did not answer our call, status: Service Unavailable.
                        I have been informed by email. Please retry later.
                        """)
            if not alt_nm or \
                    acc_no == request.form['acc_no']:
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}:{2}/{1}?content-type=application/json".format(
                    vv_base_url, acc_no, new_variant
                )
            else:
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}:{2}/all?content-type=application/json".format(
                    vv_base_url, acc_no, new_variant
                )
                # print(vv_url)
            vv_key_var = "{0}:{1}".format(acc_no, new_variant)
            try:
                vv_data = json.loads(
                    http.request(
                        'GET',
                        vv_url,
                        headers=header
                    ).data.decode('utf-8')
                )
            except Exception:
                close_db()
                md_utilities.send_error_email(
                    md_utilities.prepare_email_html(
                        'MobiDetails error',
                        """
                        <p>VV timeout for variant {0} with args: {1} {2}.
                        """.format(
                            vv_key_var,
                            vv_url,
                            header
                        )
                    ),
                    '[MobiDetails - MD variant creation Error: VV timeout]'
                )
                return md_utilities.danger_panel(
                    new_variant,
                    """
                    Variant Validator did not return any value for the variant.
                    It is likey due to a timeout. You might want to try again.
                    """
                )
            vv_error = md_utilities.vv_internal_server_error('browser', vv_data, vv_key_var)
            if vv_error != 'vv_ok':
                close_db()
                return vv_error
            if re.search('[di][neu][psl]', new_variant):
                # need to redefine vv_key_var for indels as the variant name
                # returned by vv is likely to be different form the user's
                for key in vv_data:
                    if re.search(escape(acc_no), key):
                        vv_key_var = key
                        # print(key)
                        var_obj = re.search(r':(c\..+)$', key)
                        if var_obj:
                            new_variant = var_obj.group(1)
            vv_variant_data_check = md_utilities.check_vv_variant_data(vv_key_var, vv_data)
            # if md_utilities.check_vv_variant_data(vv_key_var, vv_data) is not True:
            if vv_variant_data_check is not True:
                close_db()
                vv_warning = md_utilities.return_vv_validation_warnings(vv_data)
                if vv_warning == '':
                    md_utilities.send_error_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails error',
                            """
                            <p>VV check failed for variant {0} with args: {1} {2} {3} {4}.
                            """.format(
                                vv_key_var,
                                vv_data,
                                vv_variant_data_check,
                                vv_url,
                                header
                            )
                        ),
                        '[MobiDetails - MD variant creation Error: VV check]'
                    )
                return md_utilities.danger_panel(
                    new_variant,
                    """
                    Variant Validator did not return a valid value for the variant.
                    {0} {1}
                    """.format(vv_variant_data_check, vv_warning)
                )
        else:
            close_db()
            return md_utilities.danger_panel(
                new_variant,
                """
                Please provide the variant name as HGVS c. nomenclature (including c.)
                """
            )

        # print('--- 4- {} seconds ---'.format((time.time() - start_time)))
        # if not canonical we annotate first the canonnical then the desired one
        # main isoform?
        can_output = None
        curs.execute(
            """
            SELECT canonical
            FROM gene
            WHERE refseq = %s
            """,
            (acc_no,)
        )
        res_main = curs.fetchone()
        if res_main['canonical'] is False:
            curs.execute(
                """
                SELECT refseq
                FROM gene
                WHERE gene_symbol = %s
                    AND canonical = 't'
                """,
                (gene,)
            )
            res_can = curs.fetchone()
            # get variant name for this transcript
            # need another call to VV
            if vv_key_var in vv_data and \
                    vv_data[vv_key_var]['primary_assembly_loci']['grch38']['hgvs_genomic_description']:
                # special code for vv
                # vv_special = ''
                # vv_provider = md_utilities.urls['rest_vv_browser']['3']
                # if re.match(rf'{vv_provider}', vv_base_url):
                #     vv_special = 'auth_'
                # vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}/{2}all?content-type=application/json".format(
                #     vv_base_url,
                #     vv_data[vv_key_var]['primary_assembly_loci']['grch38']['hgvs_genomic_description'],
                #     vv_special
                # )
                # restvv 2025 - comment all above
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}/auth_all?content-type=application/json".format(
                    vv_base_url,
                    vv_data[vv_key_var]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
                )
                try:
                    vv_full_data = json.loads(
                        http.request(
                            'GET',
                            vv_url,
                            headers=header
                        ).data.decode('utf-8')
                    )
                except Exception:
                    close_db()
                    md_utilities.send_error_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails error',
                            """
                            <p>VV timeout for variant {0} with args: {1} {2}.
                            """.format(
                                vv_key_var,
                                vv_url,
                                header
                            )
                        ),
                        '[MobiDetails - MD variant creation Error: VV timeout]'
                    )
                    return md_utilities.danger_panel(
                        vv_key_var,
                        """
                        Variant Validator did not return any value for the variant.
                        It is likey due to a timeout. You might want to try again.
                        """
                    )
                vv_key_var_can = None
                for key in vv_full_data.keys():
                    # print(vv_data[vv_key_var]['primary_assembly_loci']['grch38']['hgvs_genomic_description'])
                    if re.search(res_can['refseq'], key):
                        vv_key_var_can = key
                        var_obj = re.search(r':c\.(.+)$', key)
                        if var_obj is not None:
                            new_variant_can = var_obj.group(1)
                            original_variant_can = new_variant_can
                if vv_key_var_can:
                    can_output = md_utilities.create_var_vv(
                        vv_key_var_can, gene, res_can['refseq'], new_variant_can,
                        original_variant_can,
                        vv_full_data, 'browser', db, g
                    )
            # if non_can_output is a number => success => just get the text to display
            if isinstance(can_output, int):
                # get variant c_name
                curs.execute(
                    """
                    SELECT c_name, refseq
                    FROM variant_feature
                    WHERE id = %s
                    """,
                    (can_output,)
                )
                var_c_name = curs.fetchone()
                can_output = md_utilities.info_panel(
                    'Successfully annotated the variant on the canonical isoform',
                    '{0}:c.{1}'.format(var_c_name['refseq'], var_c_name['c_name']),
                    can_output,
                    'w3-pale-green'
                )
        output = md_utilities.create_var_vv(
            vv_key_var, gene, acc_no, new_variant,
            original_variant,
            vv_data, 'browser', db, g
        )
        # if output is a number => success => just get the text to display
        if isinstance(output, int):
            # get variant c_name
            curs.execute(
                """
                SELECT c_name, refseq
                FROM variant_feature
                WHERE id = %s
                """,
                (output,)
            )
            var_c_name = curs.fetchone()
            output = md_utilities.info_panel(
                'Successfully annotated the variant',
                '{0}:c.{1}'.format(var_c_name['refseq'], var_c_name['c_name']),
                output,
                'w3-pale-green'
            )
            if can_output:
                output = '{0}{1}'.format(can_output, output)
        close_db()
        return output
    else:
        return md_utilities.danger_panel(
            'variant creation attempt',
            'A mandatory argument is lacking or is malformed.'
        )

# -------------------------------------------------------------------
# web app - ajax to modify email prefs for logged users


@bp.route('/toggle_prefs', methods=['POST'])
@login_required
def toggle_prefs():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    match_pref_value = re.search(r'^([ft])$', request.form['pref_value'])
    match_field = re.search(r'^(email_pref|lovd_export|clinvar_check|auto_add2clinvar_check)$', request.form['field'])
    if match_pref_value and \
            match_field:
    # if re.search(r'^[ft]$', request.form['pref_value']) and \
    #         re.search(r'^(email_pref|lovd_export|clinvar_check|auto_add2clinvar_check)$', request.form['field']):
        # mobiuser_id = request.form['user_id']
        # pref = request.form['pref_value']
        # field = request.form['field']
        pref = match_pref_value.group(1)
        field = match_field.group(1)
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "UPDATE mobiuser SET {0} = '{1}' WHERE \
            id = '{2}'".format(field, pref, g.user['id'])
        )
        if re.search(r'^clinvar_check$', request.form['field']) and \
                pref == 'f':
            # in addition we modify auto_add2clinvar_check the same as clinvar_check if disabling
            curs.execute(
                """
                UPDATE mobiuser 
                SET auto_add2clinvar_check = %s
                WHERE id = %s
                """,
                (pref, g.user['id'])
            )
            # then we empty the clinvar watch list
            curs.execute(
                """
                DELETE FROM mobiuser_favourite
                WHERE mobiuser_id = %s
                    AND type = 2
                """,
                (g.user['id'],)
            )
            curs.execute(
                """
                UPDATE mobiuser_favourite
                SET type = 1
                WHERE mobiuser_id = %s
                    AND type = 3
                """,
                (g.user['id'],)
            )
        if re.search(r'^auto_add2clinvar_check$', request.form['field']) and \
                pref == 't':
            # all variants attached to this user are added to mobiuser_favourite with type 2 or upgraded to 3 (if already in favourite)
            curs.execute(
                """
                SELECT a.id
                FROM variant_feature a, mobiuser b
                WHERE a.creation_user = b.id
                    AND b.id = %s
                """,
                (g.user['id'],)
            )
            variants = curs.fetchall()
            if variants:
                for var in variants:
                    curs.execute(
                        """
                        SELECT type
                        FROM mobiuser_favourite
                        WHERE mobiuser_id = %s
                        AND feature_id = %s
                        """,
                        (g.user['id'], var['id'])
                    )
                    fav = curs.fetchone()
                    if fav:
                        if fav['type'] == 1:
                            curs.execute(
                                """
                                UPDATE mobiuser_favourite
                                SET type = 3
                                WHERE feature_id = %s
                                    AND mobiuser_id = %s
                                """,
                                (var['id'], g.user['id'])
                            )
                    else:
                        curs.execute(
                            """
                            INSERT INTO mobiuser_favourite(mobiuser_id, feature_id, type)
                            VALUES (%s, %s, 2)
                            """,
                            (g.user['id'], var['id'])
                        )
        db.commit()
        close_db()
        return 'ok'

    md_utilities.send_error_email(
        md_utilities.prepare_email_html(
            'MobiDetails error',
            """
            <p>MD failed to modify a user prefs for {0}. User id: {1} to {2}</p>
            """.format(
                request.form['field'],
                g.user['id'],
                request.form['pref_value']
            )
        ),
        '[MobiDetails - User prefs Error]'
    )
    return md_utilities.danger_panel(
        '',
        """
        Sorry, something went wrong when trying to update your preferences.
        An admin has been warned. Please try again later.
        """
    )


# -------------------------------------------------------------------
# web app - ajax to mark/unmark variants as favourite for logged users


@bp.route('/favourite', methods=['POST'])
@login_required
def favourite():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'md/index.html',
            run_mode=md_utilities.get_running_mode()
        )
    match_vf_id = re.search(r'^(\d+)$', request.form['vf_id'])
    if match_vf_id:
        vf_id = match_vf_id.group(1)
        m_fav_type_insert = 1
        m_fav_type_update = 2
        if request.form['clinvar_watch'] and \
                int(request.form['clinvar_watch']) == 1:
            m_fav_type_insert = 2
            m_fav_type_update = 1
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT type
            FROM mobiuser_favourite
            WHERE mobiuser_id = %s
                AND feature_id = %s
            """,
            (g.user['id'], vf_id)
        )
        m_fav = curs.fetchone()
        if request.form['marker'] == 'mark':
            # depends on psql mobiuser_favourite.type
            # type = 1 => favourite
            # type = 2 => clinvar
            # type = 3 => both
            # if var exists and type in (1, 2) => becomes 3
            # else insert with type = 1
            if m_fav:
                if m_fav['type'] == 2 or \
                        m_fav['type'] == 1:
                    curs.execute(
                        """
                        UPDATE mobiuser_favourite
                        SET type = 3
                        WHERE mobiuser_id = %s
                            AND feature_id = %s
                        """,
                        (g.user['id'], vf_id)
                    )
            else:
                curs.execute(
                    """
                    INSERT INTO mobiuser_favourite (mobiuser_id, feature_id, type)
                    VALUES (%s, %s, %s)
                    """,
                    (g.user['id'], vf_id, m_fav_type_insert)
                )
        else:
            # depends on psql mobiuser_favourite.type
            # type = 1 => favourite
            # type = 2 => clinvar
            # type = 3 => both
            # if var exists and type == 3 => type = 2 or 1 if coming from clinvar_watch
            # else (if type in (1,2)) => delete
            if m_fav:
                # print(m_fav['type'])
                if m_fav['type'] == 3:
                    curs.execute(
                        """
                        UPDATE mobiuser_favourite
                        SET type = %s
                        WHERE mobiuser_id = %s
                            AND feature_id = %s
                        """,
                        (m_fav_type_update, g.user['id'], vf_id)
                    )
                else:
                    curs.execute(
                        """
                        DELETE FROM mobiuser_favourite
                        WHERE mobiuser_id = %s
                            AND feature_id = %s
                        """,
                        (g.user['id'], vf_id)
                    )
        db.commit()
        close_db()
        return 'ok'
    else:
        flash(
            """
            Cannot mark a variant without id! Please contact us.
            """,
            'w3-pale-red'
        )
        return 'notok'

# -------------------------------------------------------------------
# web app - ajax to empty a list of favourite variants for logged users


@bp.route('/empty_favourite_list', methods=['POST'])
@login_required
def empty_favourite_list():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'auth/profile.html',
            run_mode=md_utilities.get_running_mode()
        )
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        """
        DELETE FROM mobiuser_favourite
        WHERE mobiuser_id = %s
        """,
        (g.user['id'],)
    )
    db.commit()
    close_db()
    return 'success'

# -------------------------------------------------------------------
# web app - ajax to lock/unlock a variant list


@bp.route('/toggle_lock_variant_list/<string:list_name>', methods=['GET'])
@login_required
def toggle_lock_variant_list(list_name):
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'auth/profile.html',
            run_mode=md_utilities.get_running_mode()
        )
    match_list_name = re.search(r'^([\w]+)$', list_name)
    if len(list_name) < 31 and \
            match_list_name:
        checked_list_name = match_list_name.group(1)
    # if len(list_name) < 31 and \
    #         re.search(r'^[\w]+$', list_name):
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # check whether list exists and belongs to user
        # and get lock status
        curs.execute(
            """
            SELECT lock
            FROM variants_groups
            WHERE mobiuser_id = %s
                AND list_name = %s
            """,
            (g.user['id'], checked_list_name)
        )
        res = curs.fetchone()
        if res:
            new_lock = 'f' if res['lock'] is True else 't'
            curs.execute(
                """
                UPDATE variants_groups
                SET lock = %s
                WHERE mobiuser_id = %s
                    AND list_name = %s
                """,
                (new_lock, g.user['id'], checked_list_name)
            )
            db.commit()
            close_db()
            return 'unlocked' if new_lock == 'f' else 'locked'
        else:
            close_db()
            return 'failed'
    else:
        return 'failed'

# -------------------------------------------------------------------
# web app - ajax to generate a unique URL corresponding to a list of favourite variants


@bp.route('/create_unique_url', methods=['POST'])
@login_required
def create_unique_url():
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'auth/profile.html',
            run_mode=md_utilities.get_running_mode()
        )
    if request.form['list_name']:
        match_list_name = re.search(r'^([\w]+)$', request.form['list_name'])
        if match_list_name:
            list_name = match_list_name.group(1)
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT a.id
                FROM variant_feature a, mobiuser_favourite b
                WHERE  a.id = b.feature_id
                    AND b.mobiuser_id = %s
                ORDER BY a.gene_symbol, a.ng_name
                """,
                (g.user['id'],)
            )
            variants_favourite = curs.fetchall()
            # returns [[x], [y]]... we want [x,y]
            variants_favourite_list = [id for [id] in variants_favourite]
            # check we do not already have the same list of variants or name
            curs.execute(
                """
                SELECT tinyurl, list_name
                FROM variants_groups
                WHERE variant_ids = %s
                    OR list_name = %s
                """,
                (variants_favourite_list, list_name)
            )
            control = curs.fetchone()
            if control:
                close_db()
                return md_utilities.danger_panel(
                    '',
                    """
                    This list already exists with the name \'{0}\' and short URL: <a href="{1}" target="_blank">{1}</a>
                    """.format(
                        control['list_name'], control['tinyurl']
                    )
                )
            today = datetime.datetime.now()
            # date
            creation_date = '{0}-{1}-{2}'.format(
                today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
            )
            # get tinyurl
            # headers
            tinyurl = ''
            header = md_utilities.api_agent
            header['Content-Type'] = 'application/json'
            # https://swagger.io/docs/specification/authentication/bearer-authentication/
            header['Authorization'] = 'Bearer {}'.format(md_utilities.get_tinyurl_api_key())
            tinyurl_dict = {
                'domain': 'tinyurl.com',
                'url': url_for('auth.variant_list', list_name=list_name, _external=True)
            }
            try:
                tinyurl_json = json.loads(
                    http.request(
                        'POST',
                        md_utilities.urls['tinyurl_api'],
                        body=json.dumps(tinyurl_dict).encode('utf-8'),
                        headers=header
                    ).data.decode('utf-8')
                )
                if str(tinyurl_json['code']) == '0' and \
                        str(tinyurl_json['data']['url']) == str(url_for(
                            'auth.variant_list', list_name=list_name, _external=True
                        )):
                    tinyurl = tinyurl_json['data']['tiny_url']
            except Exception as e:
                md_utilities.send_error_email(
                    md_utilities.prepare_email_html(
                        'MobiDetails error',
                        """
                        <p>TinyURL service failed for {0} with args: {1}, json sent: {2}</p>
                        """.format(g.user['id'], e.args, tinyurl_json)
                    ),
                    '[MobiDetails - MD tinyurl Error]'
                )
                close_db()
                return md_utilities.danger_panel(
                    '',
                    """
                    Sorry, something went wrong with the creation of your list. An admin has been warned.
                    """
                )
            curs.execute(
                """
                INSERT INTO variants_groups(list_name, tinyurl, mobiuser_id, creation_date, variant_ids)
                VALUES(%s, %s, %s, %s, %s)
                """,
                (list_name, tinyurl, g.user['id'], creation_date, variants_favourite_list)
            )
            db.commit()
            close_db()
            # return 'ok'
            return md_utilities.info_panel(
                """
                <div>Your list \'{0}\' was successfully created:<br />
                    <ul>
                        <li>Unique tiny URL: <a href="{1}" target="_blank">{1}</a></li>
                        <li>Unique full URL: <a href="{2}" target="_blank">{2}</a></li>
                    </ul>
                    <span>You will have to reload the page to see it in your list of variants section.</span>
                </div>
                """.format(
                    list_name,
                    tinyurl,
                    url_for('auth.variant_list', list_name=list_name, _external=True)
                ),
                color_class='w3-pale-green'
            )
        else:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    '<p>TinyURL service failed for \
                    {0}</p>'.format(g.user['id'])
                ),
                '[MobiDetails - MD tinyurl Error]'
            )
            return md_utilities.danger_panel(
                '',
                """
                Sorry, something went wrong with the creation of your list. An admin has been warned.
                """
            )
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails error',
                '<p>TinyURL service failed for \
                {0}</p>'.format(g.user['id'])
            ),
            '[MobiDetails - MD tinyurl Error]'
        )
        return md_utilities.danger_panel(
            '',
            """
            Sorry, something went wrong with the creation of your list. An admin has been warned.
            """
        )

# -------------------------------------------------------------------
# web app - ajax to generate a unique URL corresponding to a list of favourite variants


@bp.route('/delete_variant_list/<string:list_name>', methods=['GET'])
@login_required
def delete_variant_list(list_name):
    if (md_utilities.get_running_mode() == 'maintenance'):
        return render_template(
            'auth/profile.html',
            run_mode=md_utilities.get_running_mode()
        )
    match_list_name = re.search(r'^([\w]+)$', list_name)
    if match_list_name:
        checked_list_name = match_list_name.group(1)
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            DELETE FROM variants_groups
            WHERE list_name = %s
                AND mobiuser_id = %s
            """,
            (checked_list_name, g.user['id'])
        )
        db.commit()
        close_db()
        return 'success'
    else:
        return 'failed'

# -------------------------------------------------------------------
# web app - ajax for search engine autocomplete


@bp.route('/autocomplete', methods=['POST'])
def autocomplete():
    if 'query_engine' in request.form:
        query = request.form['query_engine']
        query = re.sub(r'\s', '', query)
        query = re.sub(r"'", '', query)
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # match_object = re.search(r'^c\.([\w\d>_\*-]+)', query)
        match_obj = re.search(r'^rs(\d+)$', query)
        if match_obj:
            md_query = match_obj.group(1)
            curs.execute(
                """
                SELECT dbsnp_id
                FROM variant_feature
                WHERE dbsnp_id LIKE '{}%'
                ORDER BY dbsnp_id
                LIMIT 10
                """.format(md_query)
            )
            res = curs.fetchall()
            result = []
            for var in res:
                result.append('rs{}'.format(var[0]))
            if result is not None:
                close_db()
                return json.dumps(result)
            else:
                close_db()
                return ('', 204)
        variant_regexp = md_utilities.regexp['variant']
        match_object = re.search(rf'^c\.({variant_regexp})', query)
        if match_object:
            md_query = match_object.group(1)
            curs.execute(
                """
                SELECT DISTINCT(c_name) as name, refseq
                FROM variant_feature
                WHERE c_name LIKE '{}%'
                ORDER BY c_name LIMIT 10
                """.format(md_query)
            )
            res = curs.fetchall()
            result = []
            for var in res:
                result.append(
                    '{0}:c.{1}'.format(
                        var['refseq'],
                        var['name']
                    )
                )
            # print(json.dumps(result))
            if result is not None:
                close_db()
                return json.dumps(result)
            else:
                close_db()
                return ('', 204)
        col = 'gene_symbol'
        match_obj_nm = re.search(r'^([Nn][Mm]_.+)$', query)
        match_obj_gene = re.search(r'^([A-Za-z0-9-]+)$', query)
        if match_obj_nm:
            col = 'refseq'
            query = match_obj_nm.group(1).upper()
        elif not re.search(r'orf', query) and \
                match_obj_gene:
            query = match_obj_gene.group(1).upper()
        elif match_obj_gene:
            query = match_obj_gene.group(1)
        else:
            close_db()
            return ('', 204)
        curs.execute(
            """
            SELECT DISTINCT gene_symbol
            FROM gene
            WHERE {0} LIKE \'%{1}%'
            ORDER BY gene_symbol
            LIMIT 5
            """.format(col, query)
        )
        res = curs.fetchall()
        result = []
        for gene in res:
            result.append(gene[0])
        close_db()
        if result is not None:
            return json.dumps(result)
        else:
            return ('', 204)
    return ('', 204)
# -------------------------------------------------------------------
# web app - ajax for variant creation autocomplete


@bp.route('/autocomplete_var', methods=['POST'])
def autocomplete_var():
    if 'query_engine' in request.form and \
            'acc_no' in request.form:
        query = request.form['query_engine']
        query = re.sub(r'\s', '', query)
        query = re.sub(r"'", '', query)
        # match_obj_gene = re.search(r'^([A-Za-z0-9-]+)$', request.form['gene'])
        ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
        match_obj_nm = re.search(rf'^({ncbi_transcript_regexp})$', request.form['acc_no'])
        # gene = request.form['gene']
        # match_object = re.search(r'^c\.([\w\d>_\*-]+)', query)
        variant_regexp = md_utilities.regexp['variant']
        match_object = re.search(rf'^c\.({variant_regexp})', query)
        if match_object and \
                match_obj_nm:
            md_query = match_object.group(1)
            acc_no = match_obj_nm.group(1)
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT c_name
                FROM variant_feature
                WHERE refseq = '{0}'
                    AND c_name LIKE '{1}%'
                ORDER BY c_name
                LIMIT 10
                """.format(
                    acc_no, md_query
                )
            )
            res = curs.fetchall()
            result = []
            for var in res:
                result.append('c.{}'.format(var[0]))
            # print(json.dumps(result))
            close_db()
            if result is not None:
                return json.dumps(result)
            else:
                return ('', 204)
    # print(request.form)
    return ('', 204)

# -------------------------------------------------------------------
# web app - ajax to search for panelapp entry


@bp.route('/is_panelapp_entity', methods=['POST'])
def is_panelapp_entity():
    if 'gene_symbol' in request.form:
        gene_symbol_regexp = md_utilities.regexp['gene_symbol']
        match_obj = re.search(rf'^({gene_symbol_regexp})$', request.form['gene_symbol'])
        if match_obj:
            gene_symbol = match_obj.group(1)
            # gene_symbol = request.form['gene_symbol']
            try:
                panelapp = json.loads(
                                http.request(
                                    'GET',
                                    '{0}genes/{1}/'.format(
                                        md_utilities.urls['panelapp_api'],
                                        gene_symbol
                                    ),
                                    headers=md_utilities.api_agent
                                ).data.decode('utf-8')
                            )
            except Exception:
                return """
                <span class="w3-padding">Unable to perform the PanelApp query</span>
                """
            # panelapp = None
            md_utilities.urls['panel_app'] = None
            if panelapp is not None and \
                    str(panelapp['count']) != '0':
                # we can propose the link
                return """
                <span class="w3-button" onclick="window.open(\'{0}\', \'_blank\')">PanelApp</span>
                """.format(
                        '{0}panels/entities/{1}'.format(
                                md_utilities.urls['panelapp'],
                                escape(gene_symbol)
                            )
                    )
            else:
                return """
                <span class="w3-padding">No entry in panelApp for this gene</span>
                """
        else:
            return """
            <span class="w3-padding">Invalid character in the gene symbol</span>
            """
    else:
        return """
        <span class="w3-padding">Unable to perform the PanelApp query</span>
        """


# -------------------------------------------------------------------
# web app - ajax to run SPiP


@bp.route('/spip', methods=['POST'])
def spip():
    match_variant_id = re.search(r'^(\d+)$', request.form['variant_id'])        
    variant_regexp = md_utilities.regexp['variant']
    match_variant = re.search(rf'^c\.({variant_regexp})$', request.form['c_name'])
    gene_symbol_regexp = md_utilities.regexp['gene_symbol']
    match_gene_symbol = re.search(rf'^({gene_symbol_regexp})$', request.form['gene_symbol'])
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    match_nm_acc = re.search(rf'^({ncbi_transcript_regexp})$', request.form['nm_acc'])
    if match_variant_id and \
            match_variant and \
            match_gene_symbol and \
            match_nm_acc:
        gene_symbol = match_gene_symbol.group(1)
        nm_acc = match_nm_acc.group(1)
        c_name = match_variant.group(1)
        variant_id = match_variant_id.group(1)
        spip_cache = 0
        if os.path.exists(
                '{0}{1}.txt'.format(md_utilities.local_files['spip']['abs_path'], variant_id)
                ):
            with open(r'{0}{1}.txt'.format(md_utilities.local_files['spip']['abs_path'], variant_id)) as spip_file:
                num_lines = len(spip_file.readlines())
            if num_lines == 2:
                with open('{0}{1}.txt'.format(md_utilities.local_files['spip']['abs_path'], variant_id), "r") as spip_out:
                    result_spip = spip_out.read()
                    spip_cache = 1
        if spip_cache == 0:
            result_spip = md_utilities.run_spip(gene_symbol, nm_acc, c_name, variant_id)
        if result_spip == 'There has been an error while processing SPiP':
            return result_spip

        dict_spip = md_utilities.format_spip_result(result_spip, 'browser')
        return render_template('ajax/spip.html', spip_results=dict_spip)
    else:
        return 'received bad parameters to run SPiP.'

# -------------------------------------------------------------------
# web app - ajax to run spliceAI500


@bp.route('/spliceai_lookup', methods=['POST'])
def spliceai_lookup():
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    match_obj_variant = re.search(rf'(chr{nochr_chrom_regexp}-\d+-[ATGC]+-[ATGC]+$)', request.form['variant'])
    match_obj_transcript = re.search(rf'({ncbi_transcript_regexp})', request.form['transcript'])
    header = md_utilities.api_agent
    if match_obj_variant and \
            match_obj_transcript:
        variant = match_obj_variant.group(1)
        transcript = match_obj_transcript.group(1).split(".")[0]
        # print('{0}{1}'.format(
        #     md_utilities.urls['spliceai_api'],
        #     variant))
        try:
            spliceai500 = json.loads(
                http.request(
                    'GET',
                    '{0}{1}'.format(
                        md_utilities.urls['spliceai_api'],
                        variant
                    ),
                    headers=header
                ).data.decode('utf-8')
            )
        # except urllib3.exceptions.MaxRetryError:
        #     try:
        #         http_dangerous = urllib3.PoolManager(cert_reqs='CERT_NONE', ca_certs=certifi.where())
        #         spliceai500 = json.loads(
        #                     http_dangerous.request(
        #                         'GET',
        #                         '{0}{1}'.format(
        #                             md_utilities.urls['spliceai_api'],
        #                             variant
        #                         ),
        #                         headers=header
        #                     ).data.decode('utf-8')
        #                 )
        except Exception:
            return """
            <span class="w3-padding">Unable to run spliceAI lookup API - Error returned</span>
            """
        if spliceai500 and \
                spliceai500['variant'] == variant and \
                'error' not in spliceai500:
            # print(spliceai500)
            for score in spliceai500['scores']:
                # print(score)
                if 't_refseq_ids' in score and \
                        score['t_refseq_ids']:
                    for t_refseq_ids in score['t_refseq_ids']:
                        if re.search(rf'{transcript}', t_refseq_ids):
                            # AG AL DG DL
                            # new spliceAi-lookup format 20230911
                            # print(score)
                            # print(score['DP_DL'])
                            # return '{0:.2f} ({1});{2:.2f} ({3});{4:.2f} ({5});{6:.2f} ({7})'.format(
                            return '{0} ({1});{2} ({3});{4} ({5});{6} ({7})'.format(
                                score['DS_AG'],
                                score['DP_AG'],
                                score['DS_AL'],
                                score['DP_AL'],
                                score['DS_DG'],
                                score['DP_DG'],
                                score['DS_DL'],
                                score['DP_DL']
                            )
        return """
        <span class="w3-padding">No results found for transcipt {} in spliceAI lookup API results</span>
        """.format(transcript)
    else:
        return """
        <span class="w3-padding">Unable to run spliceAI lookup API (wrong parameter)</span>
        """


# -------------------------------------------------------------------
# web app - ajax to run MobiDeep


@bp.route('/mobideep', methods=['POST'])
def mobideep():
    # print(request.form['mobideep_input_scores'])
    if re.search(r'^[\w\.]+\s[\w\.-]+\s[\w\.]+\s[\w\.-]+\s[\w\.]+$', request.form['mobideep_input_scores']):
        mobideep_input_scores = request.form['mobideep_input_scores']
        mobideep_input_scores = mobideep_input_scores.replace("None", "NaN")
        # header = md_utilities.api_agent
        try:
            req_results = requests.post(
                '{0}/mobideep'.format(md_utilities.urls['spliceai_internal_server']),
                json={'mobideep_input': mobideep_input_scores},
                headers={'Content-Type': 'application/json'}
            )
        except requests.exceptions.ConnectionError:
                return '<p style="color:red">Failed to establish a connection to the MobiDeep server.</p>'
        except Exception:
            return """
            <span class="w3-padding">Unable to run MobiDeep API - Error returned</span>
            """
        # print(req_results.status_code)
        # print(req_results.content)
        if req_results.status_code == 200:
            mobideep_results = json.loads(req_results.content)
            if mobideep_results['mobideep_return_code'] == 0 and \
                    mobideep_results['error'] is None:
                # check thresholds for color
                raw_color = md_utilities.predictor_colors['min']
                log_color = md_utilities.predictor_colors['min']
                if float(mobideep_results['result']['MobiDeepRawscore']) > md_utilities.predictor_thresholds['mobideep_raw_sen']:
                        raw_color = md_utilities.predictor_colors['mid_effect']
                if float(mobideep_results['result']['MobiDeepRawscore']) > md_utilities.predictor_thresholds['mobideep_raw_spe']:
                        raw_color = md_utilities.predictor_colors['max']
                if float(mobideep_results['result']['MobiDeepLogScore']) > md_utilities.predictor_thresholds['mobideep_log_sen']:
                        log_color = md_utilities.predictor_colors['mid_effect']
                if float(mobideep_results['result']['MobiDeepLogScore']) > md_utilities.predictor_thresholds['mobideep_log_spe']:
                        log_color = md_utilities.predictor_colors['max']
                # return mobideep scores html formatted
                return """
                <span id='mobideep_raw' style='color:{0}'>{1}</span> (<span id='mobideep_log' style='color:{2}'>{3}</span>)
                """.format(
                    raw_color,
                    "{:.4f}".format(float(mobideep_results['result']['MobiDeepRawscore'])),
                    log_color,
                    "{:.4f}".format(float(mobideep_results['result']['MobiDeepLogScore']))
                )
        return """
        <span class="w3-padding">No MobiDeep score computed</span>
        """
    else:
        return """
        <span class="w3-padding">Unable to run MobiDeep API (wrong parameter)</span>
        """
