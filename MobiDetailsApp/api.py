import re
from flask import (
    Blueprint, g, request, url_for, jsonify, redirect, flash
)
import psycopg2
import psycopg2.extras
import json
import urllib3
import certifi
import urllib.parse
import datetime
from MobiDetailsApp.db import get_db, close_db
from MobiDetailsApp import md_utilities

bp = Blueprint('api', __name__)
# -------------------------------------------------------------------
# api - variant exists?


@bp.route('/api/variant/exists/<string:variant_ghgvs>')
def api_variant_exists(variant_ghgvs=None):
    if variant_ghgvs is None:
        return jsonify(mobidetails_error='No variant submitted')
    match_object = re.search(r'^([Nn][Cc]_0000\d{2}\.\d{1,2}):g\.(.+)', urllib.parse.unquote(variant_ghgvs))
    if match_object:
        db = get_db()
        # match_object = re.search(r'^([Nn][Cc]_0000\d{2}\.\d{1,2}):g\.(.+)', variant_ghgvs)
        # res_common = md_utilities.get_common_chr_name(db, match_object.group(1))
        chrom, genome_version = md_utilities.get_common_chr_name(db, match_object.group(1).upper())
        pattern = match_object.group(2)
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT feature_id FROM variant WHERE chr = %s AND g_name = %s AND genome_version = %s",
            (chrom, pattern, genome_version)
        )
        res = curs.fetchone()
        if res is not None:
            return jsonify(mobidetails_id=res['feature_id'], url='{0}{1}'.format(
                request.host_url[:-1], url_for('md.variant', variant_id=res['feature_id'])
            ))
            # return jsonify(mobidetails_id=res['feature_id'])
        else:
            # return jsonify("SELECT feature_id FROM variant WHERE g_name = 'chr{0}:g.{1}' AND genome_version = '{2}'".format(chrom, pattern, genome_version))
            return jsonify(mobidetails_warning='The variant {} does not exist yet in MD'.format(variant_ghgvs))
    else:
        return jsonify(mobidetails_error='Malformed query {}'.format(variant_ghgvs))

# -------------------------------------------------------------------
# api - variant create


# @bp.route('/api/variant/create/<string:variant_chgvs>/<string:api_key>')
# def api_variant_create(variant_chgvs=None, api_key=None):
@bp.route('/api/variant/create', methods=['POST'])
def api_variant_create(variant_chgvs=None, api_key=None):
    # print(request.form)
    # print(request.args)
    # get params
    # swagger/curl sends request.args e.g.
    # curl -X POST "http://10.34.20.79:5001/api/variant/create?variant_chgvs=NM_005422.2%3Ac.5040G%3ET&api_key=XXX" -H  "accept: application/json"
    # while
    # urllib3 request from create_vars_batch.py sends request.form
    if request.args.get('variant_chgvs') and \
            request.args.get('api_key'):
        variant_chgvs = request.args.get('variant_chgvs', type=str)
        api_key = request.args.get('api_key', type=str)
    elif 'variant_chgvs' in request.form and \
            'api_key' in request.form:
        variant_chgvs = request.form['variant_chgvs']
        api_key = request.form['api_key']
    else:
        return jsonify(mobidetails_error='I cannot fetch the right parameters')
    if variant_chgvs is not None and \
            api_key is not None:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # mobiuser_id = None
        if len(api_key) != 43:
            return jsonify(mobidetails_error='Invalid API key')
        else:
            curs.execute(
                "SELECT * FROM mobiuser WHERE api_key = %s",
                (api_key,)
            )
            res = curs.fetchone()
            if res is None:
                return jsonify(mobidetails_error='Unknown API key')
            else:
                g.user = res
        # if variant_chgvs is None:
        #     return jsonify(mobidetails_error='No variant submitted')
        match_object = re.search(r'^([Nn][Mm]_\d+)\.(\d{1,2}):c\.(.+)', urllib.parse.unquote(variant_chgvs))
        if match_object:
            # match_object = re.search(r'^([Nn][Mm]_\d+)\.(\d{1,2}):c\.(.+)', variant_chgvs)
            acc_no, acc_version, new_variant = match_object.group(1), match_object.group(2), match_object.group(3)
            new_variant = new_variant.replace(" ", "").replace("\t", "")
            # new_variant = new_variant.replace("\t", "")
            original_variant = new_variant
            curs.execute(
                "SELECT id FROM variant_feature WHERE c_name = %s AND gene_name[2] = %s",
                (new_variant, acc_no)
            )
            res = curs.fetchone()
            if res is not None:
                return jsonify(
                    mobidetails_id=res['id'],
                    url='{0}{1}'.format(
                        request.host_url[:-1],
                        url_for('md.variant', variant_id=res['id'])
                    )
                )
            else:
                # creation
                # get gene
                curs.execute(
                    "SELECT name[1] as gene FROM gene WHERE name[2] = %s",
                    (acc_no,)
                )
                res_gene = curs.fetchone()
                if res_gene is None:
                    return jsonify(mobidetails_error='The gene corresponding to {} is not yet present in MobiDetails'.format(acc_no))
                http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}.{2}:{3}/all?content-type=application/json".format(
                    md_utilities.urls['variant_validator_api'], acc_no, acc_version, new_variant
                )
                vv_key_var = "{0}.{1}:c.{2}".format(acc_no, acc_version, new_variant)

                try:
                    vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
                except Exception:
                    close_db()
                    return jsonify(mobidetails_error='Variant Validator did not return any value for the variant {}.'.format(new_variant))
                if re.search('[di][neu][psl]', new_variant):
                    # need to redefine vv_key_var for indels as the variant name returned by vv is likely to be different form the user's
                    for key in vv_data.keys():
                        if re.search('{0}.{1}'.format(acc_no, acc_version), key):
                            vv_key_var = key
                            # print(key)
                            var_obj = re.search(r':c\.(.+)$', key)
                            if var_obj is not None:
                                new_variant = var_obj.group(1)
                creation_dict = md_utilities.create_var_vv(
                    vv_key_var, res_gene['gene'], acc_no,
                    'c.{}'.format(new_variant), original_variant,
                    acc_version, vv_data, 'api', db, g
                )
                return jsonify(creation_dict)
        else:
            return jsonify(mobidetails_error='Malformed query {}'.format(variant_chgvs))
    else:
        return jsonify(mobidetails_error='Invalid parameters')
# -------------------------------------------------------------------
# api - variant create from genomic HGVS eg NC_000001.11:g.40817273T>G and gene name (HGNC)


# @bp.route('/api/variant/create_g/<string:variant_ghgvs>/<string:gene>/<string:caller>/<string:api_key>', methods=['GET', 'POST'])
# def api_variant_g_create(variant_ghgvs=None, gene=None, caller=None, api_key=None):
@bp.route('/api/variant/create_g', methods=['POST'])
def api_variant_g_create(variant_ghgvs=None, gene=None, caller=None, api_key=None):
    # get params
    if request.args.get('variant_ghgvs') and \
            request.args.get('gene_hgnc') and \
            request.args.get('caller') and \
            request.args.get('api_key'):
        variant_ghgvs = request.args.get('variant_ghgvs', type=str)
        gene = request.args.get('gene_hgnc', type=str)
        caller = request.args.get('caller', type=str)
        api_key = request.args.get('api_key', type=str)
    elif 'variant_ghgvs' in request.form and \
            'gene_hgnc' in request.form and \
            'caller' in request.form and \
            'api_key' in request.form:
        variant_ghgvs = request.form['variant_ghgvs']
        gene = request.form['gene_hgnc']
        caller = request.form['caller']
        api_key = request.form['api_key']
    else:
        return jsonify(mobidetails_error='I cannot fetch the right parameters')
    if variant_ghgvs is not None and \
            gene is not None and \
            caller is not None and \
            api_key is not None:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # mobiuser_id = None
        if len(api_key) != 43:
            return jsonify(mobidetails_error='Invalid API key')
        else:
            curs.execute(
                "SELECT * FROM mobiuser WHERE api_key = %s",
                (api_key,)
            )
            res = curs.fetchone()
            if res is None:
                return jsonify(mobidetails_error='Unknown API key')
            else:
                g.user = res
        # if variant_ghgvs is None:
        #     return jsonify(mobidetails_error='No variant submitted')
        # if gene is None:
        #     return jsonify(mobidetails_error='No gene submitted')
        if caller != 'browser' and \
                caller != 'cli':
            return jsonify(mobidetails_error='Invalid caller submitted')
        # check gene exists
        curs.execute(
            "SELECT name, nm_version FROM gene WHERE name[1] = %s AND canonical = 't'",
            (gene,)
        )
        res_gene = curs.fetchone()
        if res_gene is not None:
            match_object = re.search(r'^([Nn][Cc]_\d+\.\d{1,2}):g\.([\dATGCagctdelinsup_>]+)', urllib.parse.unquote(variant_ghgvs))
            if match_object:
                ncbi_chr, g_var = match_object.group(1), match_object.group(2)
                # 1st check hg38
                curs.execute(
                    "SELECT * FROM chromosomes WHERE ncbi_name = %s",
                    (ncbi_chr,)
                )
                res = curs.fetchone()
                if res is not None and \
                        res['genome_version'] == 'hg38':
                    genome_version, chrom = res['genome_version'], res['name']
                    # check if variant exists
                    curs.execute(
                        "SELECT feature_id FROM variant WHERE genome_version = %s AND g_name = %s AND chr = %s",
                        (genome_version, g_var, chrom)
                    )
                    res = curs.fetchone()
                    if res is not None:
                        if caller == 'cli':
                            return jsonify(
                                mobidetails_id=res['feature_id'],
                                url='{0}{1}'.format(
                                    request.host_url[:-1],
                                    url_for('md.variant', variant_id=res['feature_id'])
                                )
                            )
                        else:
                            return redirect(url_for('md.variant', variant_id=res['feature_id']))
                    else:
                        # creation
                        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                        vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}/all?content-type=application/json".format(
                            md_utilities.urls['variant_validator_api'], variant_ghgvs
                        )
                        # print(vv_url)
                        # vv_key_var = "{0}.{1}:c.{2}".format(acc_no, acc_version, new_variant)

                        try:
                            vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
                        except Exception:
                            close_db()
                            return jsonify(mobidetails_error='Variant Validator did not return any value for the variant {}.'.format(variant_ghgvs))
                        # look forg ene acc #
                        # print(vv_data)
                        new_variant = None
                        vv_key_var = None
                        for key in vv_data.keys():
                            match_obj = re.search(r'^([Nn][Mm]_\d+)\.(\d{1,2}):c\.(.+)', key)
                            if match_obj:
                                new_variant = match_obj.group(3)
                                # print("{0}-{1}-{2}-{3}".format(match_obj.group(1), res_gene['name'][1], match_obj.group(2), res_gene['nm_version']))
                                if match_obj.group(1) == res_gene['name'][1] and \
                                        str(match_obj.group(2)) == str(res_gene['nm_version']):
                                    vv_key_var = "{0}.{1}:c.{2}".format(match_obj.group(1), match_obj.group(2), match_obj.group(3))
                        if vv_key_var is not None:
                            # print(vv_key_var)
                            creation_dict = md_utilities.create_var_vv(
                                vv_key_var, res_gene['name'][0], res_gene['name'][1],
                                'c.{}'.format(new_variant), new_variant,
                                res_gene['nm_version'], vv_data, 'api', db, g
                            )
                            if caller == 'cli':
                                return jsonify(creation_dict)
                            else:
                                return redirect(url_for('md.variant', variant_id=creation_dict['mobidetails_id']))
                        else:
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Could not create variant {}.'.format(variant_ghgvs), variant_validator_output=vv_data)
                            else:
                                try:
                                    flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                          The error is the following: {}'.format(vv_data['validation_warning_1']['validation_warnings']), 'w3-pale-red')
                                except Exception:
                                    flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                          Sorry for the inconvenience. You may want to try directly in MobiDetails.', 'w3-pale-red')
                                return redirect(url_for('md.index'))

                else:
                    if caller == 'cli':
                        return jsonify(mobidetails_error='Unknown chromosome {} submitted or bad genome version (hg38 only)'.format(ncbi_chr))
                    else:
                        flash('The submitted chromosome or genome version looks corrupted (hg38 only).', 'w3-pale-red')
                        return redirect(url_for('md.index'))
            else:
                if caller == 'cli':
                    return jsonify(mobidetails_error='Malformed query {}'.format(variant_ghgvs))
                else:
                    flash('The query seems to be malformed: {}.'.format(variant_ghgvs), 'w3-pale-red')
                    return redirect(url_for('md.index'))
        else:
            if caller == 'cli':
                return jsonify(mobidetails_error='Unknown gene {} submitted'.format(gene))
            else:
                flash('Unknown gene {} submitted'.format(gene), 'w3-pale-red')
                return redirect(url_for('md.index'))
    else:
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameters')
        else:
            flash('The submitted parameters looks invalid!!!', 'w3-pale-red')
            return redirect(url_for('md.index'))
# -------------------------------------------------------------------
# api - gene


@bp.route('/api/gene/<string:gene_hgnc>')
def api_gene(gene_hgnc=None):
    if gene_hgnc is None:
        return jsonify(mobidetails_error='No gene submitted')
    if re.search(r'[^\w\.-]', gene_hgnc):
        return jsonify(mobidetails_error='Invalid gene submitted ({})'.format(gene_hgnc))
    research = gene_hgnc
    search_id = 1
    match_obj = re.search(r'(NM_\d+)\.?\d?', gene_hgnc)
    if match_obj:
        # we have a RefSeq accession number
        research = match_obj.group(1)
        search_id = 2
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        "SELECT * FROM gene WHERE name[%s] = %s",
        (search_id, research)
    )
    res = curs.fetchall()
    d_gene = {}
    if res:
        for transcript in res:
            if 'HGNC' not in d_gene:
                d_gene['HGNC'] = transcript['name'][0]
            if 'chr' not in d_gene:
                d_gene['Chr'] = transcript['chr']
            if 'strand' not in d_gene:
                d_gene['Strand'] = transcript['strand']
            if 'ng' not in d_gene:
                if transcript['ng'] == 'NG_000000.0':
                    d_gene['RefGene'] = 'No RefGene in MobiDetails'
                else:
                    d_gene['RefGene'] = transcript['ng']
            refseq = '{0}.{1}'.format(transcript['name'][1], transcript['nm_version'])
            d_gene[refseq] = {
                'canonical': transcript['canonical'],
            }
            if 'RefProtein' not in d_gene[refseq]:
                if transcript['np'] == 'NP_000000.0':
                    d_gene[refseq]['RefProtein'] = 'No RefProtein in MobiDetails'
                else:
                    d_gene[refseq]['RefProtein'] = transcript['np']
            if 'UNIPROT' not in d_gene[refseq]:
                d_gene[refseq]['UNIPROT'] = transcript['uniprot_id']
            if 'variantCreationTag' not in d_gene[refseq]:
                d_gene[refseq]['variantCreationTag'] = transcript['variant_creation']
        return jsonify(d_gene)
    else:
        return jsonify(mobidetails_warning='Unknown gene ({})'.format(gene_hgnc))

# -------------------------------------------------------------------
# api - update class


# @bp.route('/api/variant/update_acmg/<int:variant_id>/<int:acmg_id>/<string:api_key>')
# def api_update_acmg(variant_id=None, acmg_id=None, api_key=None):
@bp.route('/api/variant/update_acmg', methods=['POST'])
def api_update_acmg(variant_id=None, acmg_id=None, api_key=None):
    # get params
    if request.args.get('variant_id') and \
            request.args.get('acmg_id') and \
            request.args.get('api_key'):
        variant_id = request.args.get('variant_id', type=int)
        acmg_id = request.args.get('acmg_id', type=int)
        api_key = request.args.get('api_key', type=str)
    elif 'variant_id' in request.form and \
            'acmg_id' in request.form and \
            'api_key' in request.form:
        variant_id = request.form['variant_id']
        acmg_id = request.form['acmg_id']
        api_key = request.form['api_key']
    else:
        return jsonify(mobidetails_error='I cannot fetch the right parameters')
    if variant_id is not None and \
            acmg_id is not None and \
            api_key is not None:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # mobiuser_id = None
        if len(api_key) != 43:
            return jsonify(mobidetails_error='Invalid API key')
        else:
            curs.execute(
                "SELECT * FROM mobiuser WHERE api_key = %s",
                (api_key,)
            )
            res = curs.fetchone()
            if res is None:
                return jsonify(mobidetails_error='Unknown API key')
            else:
                g.user = res
        # if not isinstance(variant_id, int):
        # request.form data are str
        if not isinstance(variant_id, int):
            if not re.search(r'^\d+$', variant_id):
                return jsonify(mobidetails_error='No or invalid variant id submitted')
            else:
                variant_id = int(variant_id)
            # if not isinstance(acmg_id, int):
            if not re.search(r'^\d+$', acmg_id):
                return jsonify(mobidetails_error='No or invalid ACMG class submitted')
            else:
                acmg_id = int(acmg_id)
        if acmg_id > 0 and acmg_id < 7:
            # variant exists?
            curs.execute(
                "SELECT id FROM variant_feature WHERE id = %s",
                (variant_id,)
            )
            res = curs.fetchone()
            if res:
                # variant has already this class w/ this user?
                curs.execute(
                    "SELECT variant_feature_id FROM class_history WHERE variant_feature_id = %s AND mobiuser_id = %s AND acmg_class = %s",
                    (variant_id, g.user['id'], acmg_id)
                )
                res = curs.fetchone()
                if res:
                    return jsonify(mobidetails_error='ACMG class already submitted by this user for this variant')
                today = datetime.datetime.now()
                date = '{0}-{1}-{2}'.format(
                    today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
                )
                curs.execute(
                    "INSERT INTO class_history (variant_feature_id, acmg_class, mobiuser_id, class_date) VALUES (%s, %s, %s, %s)",
                    (variant_id, acmg_id, g.user['id'], date)
                )
                db.commit()
                d_update = {
                    'variant_id': variant_id,
                    'new_acmg_class': acmg_id,
                    'mobiuser_id': g.user['id'],
                    'date': date
                }
                return jsonify(d_update)
            else:
                return jsonify(mobidetails_error='Invalid variant id submitted')
        else:
            return jsonify(mobidetails_error='Invalid ACMG class submitted')
    else:
        return jsonify(mobidetails_error='Invalid parameters')
