import os
import re
from flask import (
    Blueprint, flash, g, render_template, request
)
from werkzeug.urls import url_parse
from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db, close_db
from . import md_utilities

import psycopg2
import psycopg2.extras
import json
import urllib3
import certifi
import datetime

bp = Blueprint('ajax', __name__)





######################################################################
# web app - ajax for litvar


@bp.route('/litVar', methods=['POST'])
def litvar():
    if re.search(r'^rs\d+$', request.form['rsid']):
        rsid = request.form['rsid']
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        litvar_data = None
        # litvar_url = "{0}{1}%23%23%22%5D%7D".format(md_utilities.urls['ncbi_litvar_api'], rsid)
        litvar_url = "{0}{1}".format(md_utilities.urls['ncbi_litvar_api'], rsid)
        try:
            litvar_data = json.loads(http.request('GET', litvar_url).data.decode('utf-8'))
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    '<p>Litvar API call failed in {0} with args: {1}</p>'.format(
                        os.path.basename(__file__), e.args
                    )
                ),
                '[MobiDetails - API Error]'
            )
        if litvar_data is not None:
            # if len(litvar_data) == 0: or re.search(r'mandatory', litvar_data[0])
            if len(litvar_data) == 0:
                return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'
            return render_template('ajax/litvar.html', urls=md_utilities.urls, pmids=litvar_data[0]['pmids'])
        else:
            return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'
    else:
        return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'

######################################################################
# web app - ajax for defgen export file


@bp.route('/defgen', methods=['POST'])
def defgen():
    if re.search(r'^\d+$', request.form['vfid']) and \
            re.search(rf'^{md_utilities.genome_regexp}$', request.form['genome']):
        variant_id = request.form['vfid']
        genome = request.form['genome']
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # get all variant_features and gene info
        curs.execute(
            "SELECT * FROM variant_feature a, variant b, gene c WHERE \
            a.id = b.feature_id AND a.gene_name = c.name AND a.id = '{0}'\
            AND b.genome_version = '{1}'".format(variant_id, genome)
        )
        vf = curs.fetchone()
        file_content = "GENE;VARIANT;A_ENREGISTRER;ETAT;RESULTAT;VARIANT_P;VARIANT_C;ENST;NM;POSITION_GENOMIQUE;CLASSESUR5;CLASSESUR3;COSMIC;RS;REFERENCES;CONSEQUENCES;COMMENTAIRE;CHROMOSOME;GENOME_REFERENCE;NOMENCLATURE_HGVS;LOCALISATION;SEQUENCE_REF;LOCUS;ALLELE1;ALLELE2\r\n"

        file_content += "{0};{1}.{2}:c.{3};;;;p.{4};c.{3};{5};{1}.{2};{6};{7};;;rs{8};;{9};;chr{10};{11};chr{10}:g.{12};{13} {14};;;;\r\n".format(
            vf['gene_name'][0], vf['gene_name'][1], vf['nm_version'], vf['c_name'], vf['p_name'], vf['enst'], vf['pos'], vf['acmg_class'],
            vf['dbsnp_id'], vf['prot_type'], vf['chr'], genome, vf['g_name'], vf['start_segment_type'], vf['start_segment_number']
        )
        # print(file_content)
        app_path = os.path.dirname(os.path.realpath(__file__))
        file_loc = "defgen/{0}-{1}-{2}{3}-{4}.csv".format(genome, vf['chr'], vf['pos'], vf['pos_ref'], vf['pos_alt'])
        defgen_file = open("{0}/static/{1}".format(app_path, file_loc), "w")
        defgen_file.write(file_content)
        close_db()
        return render_template('ajax/defgen.html', variant="{0}.{1}:c.{2}".format(
            vf['gene_name'][1], vf['nm_version'], vf['c_name']), defgen_file=file_loc, genome=genome)
    else:
        close_db()
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails Ajax error',
                '<p>DefGen file generation failed in {} (no variant_id)</p>'.format(
                    os.path.basename(__file__)
                )
            ),
            '[MobiDetails - Ajax Error]'
        )
        return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">Impossible to create DEFGEN file</div>'

# -------------------------------------------------------------------
# web app - ajax for intervar API


@bp.route('/intervar', methods=['POST'])
def intervar():
    if re.search(rf'^{md_utilities.genome_regexp}$', request.form['genome']) and \
            re.search(rf'^{md_utilities.nochr_chrom_regexp}$', request.form['chrom']) and \
            re.search(r'^\d+$', request.form['pos']) and \
            re.search(r'^[ATGC]+$', request.form['ref']) and \
            re.search(r'^[ATGC]+$', request.form['alt']):
        genome = request.form['genome']
        chrom = request.form['chrom']
        pos = request.form['pos']
        ref = request.form['ref']
        alt = request.form['alt']
        if len(ref) > 1 or len(alt) > 1:
            return 'No wintervar for indels'
        if ref == alt:
            return 'hg19 reference is equal to variant: no wIntervar query'
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        intervar_url = "{0}{1}_updated.v.201904&chr={2}&pos={3}&ref={4}&alt={5}".format(
            md_utilities.urls['intervar_api'], genome, chrom,
            pos, ref, alt
        )
        try:
            intervar_data = json.loads(http.request('GET', intervar_url).data.decode('utf-8'))
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails API error',
                    '<p>Intervar API call failed for {0}-{1}-{2}-{3}-{4}<br /> - from {5} with args: {6}</p>'.format(
                        genome, chrom, pos, ref,
                        alt, os.path.basename(__file__), e.args
                    )
                ),
                '[MobiDetails - API Error]'
            )
            return "<span>No wintervar class</span>"
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT html_code FROM valid_class WHERE acmg_translation = '{}'".format(
                intervar_data['Intervar'].lower()
            )
        )
        res = curs.fetchone()
        close_db()
        return "<span style='color:{0};'>{1}</span>".format(res['html_code'], intervar_data['Intervar'])
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails API error',
                '<p>Intervar API call failed for {0}-{1}-{2}-{3}-{4}<br /> - from {5} with args: A mandatory argument is missing</p>'.format(
                    genome, chrom, pos, ref,
                    alt, os.path.basename(__file__)
                )
            ),
            '[MobiDetails - API Error]'
        )
        return "<span>No wintervar class</span>"

# -------------------------------------------------------------------
# web app - ajax for LOVD API


@bp.route('/lovd', methods=['POST'])
def lovd():
    genome = chrom = g_name = c_name = None
    # print(request.form)
    if re.search(rf'^{md_utilities.genome_regexp}$', request.form['genome']) and \
            re.search(rf'^{md_utilities.nochr_chrom_regexp}$', request.form['chrom']) and \
            re.search(rf'^{md_utilities.variant_regexp}$', request.form['g_name']) and \
            re.search(rf'^c\.{md_utilities.variant_regexp}$', request.form['c_name']):
        genome = request.form['genome']
        chrom = request.form['chrom']
        g_name = request.form['g_name']
        c_name = request.form['c_name']
        if re.search(r'=', g_name):
            return 'hg19 reference is equal to variant: no LOVD query'
        positions = md_utilities.compute_start_end_pos(g_name)
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        # http://www.lovd.nl/search.php?build=hg19&position=chr$evs_chr:".$evs_pos_start."_".$evs_pos_end
        lovd_url = "{0}search.php?build={1}&position=chr{2}:{3}_{4}".format(md_utilities.urls['lovd'], genome, chrom, positions[0], positions[1])
        # print(lovd_url)
        lovd_data = None
        try:
            lovd_data = re.split('\n', http.request('GET', lovd_url).data.decode('utf-8'))
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
            if len(lovd_data) == 1:
                return 'No match in LOVD public instances'
            lovd_data.remove('"hg_build"\t"g_position"\t"gene_id"\t"nm_accession"\t"DNA"\t"url"')
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
                    if fields[4] == c_name or re.match(c_name, fields[4]):
                        lovd_urls.append(fields[5])
            if len(lovd_urls) > 0:
                for url in lovd_urls:
                    lovd_name = None
                    url = url.replace('"', '')
                    lovd_base_url = '{0}://{1}{2}'.format(url_parse(url).scheme, url_parse(url).host, url_parse(url).path)
                    match_obj = re.search(r'^(.+\/)variants\.php$', lovd_base_url)
                    if match_obj:
                        lovd_base_url = match_obj.group(1)
                        try:                       
                            lovd_fh = open(md_utilities.lovd_ref_file)
                            for line in lovd_fh:
                                if re.search(r'{}'.format(lovd_base_url), line):
                                    lovd_name = line.split('\t')[0]
                        except Exception:
                            pass
                    html_li = '<li>'
                    html_li_end = '</li>'
                    if len(lovd_urls) == 1:
                        html_li = ''
                        html_li_end = ''
                    if lovd_name is not None:
                        html_list.append("{0}<a href='{1}' target='_blank'>{2}</a>{3}".format(html_li, url, lovd_name, html_li_end))
                    else:
                        html_list.append("{0}<a href='{1}' target='_blank'>Link {2}</a>{3}".format(html_li, url, i, html_li_end))
                    i += 1
            else:
                return 'No match in LOVD public instances'
            html = '<ul>{}</ul>'.format(''.join(html_list))
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
            return "LOVD service looks down"
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails API error',
                '<p>LOVD API call failed in {0} with args: a mandatory argument is missing</p>'.format(
                    os.path.basename(__file__)
                )
            ),
            '[MobiDetails - API Error]'
        )
        return "LOVD query malformed"
    # return "<span>{0}</span><span>{1}</span>".format(lovd_data, lovd_url)

# -------------------------------------------------------------------
# web app - ajax for ACMG classification modification


@bp.route('/modif_class', methods=['POST'])
@login_required
def modif_class():
    # tr_html = 'notok'
    if re.search(r'^\d+$', request.form['variant_id']) and \
            re.search(r'^\d+$', request.form['acmg_select']):
        variant_id = request.form['variant_id']
        acmg_select = request.form['acmg_select']
        acmg_comment = request.form['acmg_comment']
        today = datetime.datetime.now()
        date = '{0}-{1}-{2}'.format(
            today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
        )

        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # get all variant_features and gene info
        try:
            curs.execute(
                "SELECT class_date FROM class_history WHERE \
                    variant_feature_id = %s AND acmg_class = %s \
                    AND mobiuser_id = %s",
                (variant_id, acmg_select, g.user['id'])
            )
            res = curs.fetchone()
            if res is not None:
                if str(res['class_date']) == str(date):
                    # print(("{0}-{1}").format(res['class_date'], date))
                    tr_html = "<tr id='already_classified'><td colspan='4'>\
                              You already classified this variant with the same class today.\
                              If you just want to modify comments, the previous classification and start from scratch.\
                              </td></tr>"
                    return tr_html
                curs.execute(
                    "UPDATE class_history SET class_date  = %s, comment = %s WHERE \
                        variant_feature_id = %s AND acmg_class = %s \
                        AND mobiuser_id = %s",
                    (date, acmg_comment, variant_id, acmg_select, g.user['id'])
                )
            else:
                curs.execute(
                    "INSERT INTO class_history (variant_feature_id, acmg_class, mobiuser_id, class_date, comment) VALUES \
                        (%s, %s, %s, %s, %s )",
                    (variant_id, acmg_select, g.user['id'], date, acmg_comment)
                )
            db.commit()
            # curs.execute(
            #     "SELECT username FROM mobiuser WHERE id = '{}'".format(g.user['id'])
            # )
            # mobiuser_name = curs.fetchone()
            curs.execute(
                "SELECT html_code, acmg_translation FROM valid_class WHERE acmg_class = %s",
                (acmg_select,)
            )
            acmg_details = curs.fetchone()
            tr_html = "<tr id='{0}-{1}-{2}'> \
                    <td class='w3-left-align'>{3}</td> \
                    <td class='w3-left-align'>{4}</td> \
                    <td class='w3-left-align'> \
                        <span style='color:{5};'>Class {1} ({6})</span>\
                    </td> \
                    <td> \
                        <div class='w3-cell-row'> \
                            <span class='w3-container w3-left-align w3-cell'>{7}</span>\
                </tr>".format(
                    g.user['id'],
                    acmg_select,
                    variant_id,
                    g.user['username'],
                    date,
                    acmg_details['html_code'],
                    acmg_details['acmg_translation'],
                    acmg_comment
                )
            return tr_html
        except Exception as e:
            # pass
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    '<p>Variant class modification failed for variant {0} with args: {1}</p>'.format(variant_id, e.args)
                ),
                '[MobiDetails - MD variant class Error]'
            )
            return md_utilities.danger_panel('', 'Sorry, something went wrong with the addition of this annotation. An admin has been warned.')
            # flash('Sorry, for some reason, variant class modification failed. The admin has been warned.', 'w3-pale-red')
        
        # return redirect(url_for('md.variant', variant_id=variant_id, _anchor='class'))
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails error',
                '<p>Variant class modification failed for variant {0} with args: wrong parameter {1}-{2}</p>'.format(
                    variant_id,
                    request.form['variant_id'],
                    request.form['acmg_select']
                )
            ),
            '[MobiDetails - MD variant class Error]'
        )
        return md_utilities.danger_panel('', 'Sorry, something went wrong with the addition of this annotation. An admin has been warned.')
    # return redirect(url_for('md.index'))


# -------------------------------------------------------------------
# web app - ajax to remove ACMG classification


@bp.route('/remove_class', methods=['POST'])
@login_required
def remove_class():
    if re.search(r'^\d+$', request.form['variant_id']) and \
            re.search(r'^\d+$', request.form['acmg_class']):
        variant_id = request.form['variant_id']
        acmg_class = request.form['acmg_class']
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            curs.execute(
                "DELETE FROM class_history WHERE \
                    variant_feature_id = %s AND acmg_class = %s \
                    AND mobiuser_id = %s",
                (variant_id, acmg_class, g.user['id'])
            )
            db.commit()
            return 'ok'
        except Exception as e:
            md_utilities.send_error_email(
                md_utilities.prepare_email_html(
                    'MobiDetails error',
                    '<p>Variant class deletion failed for {0} with args: {1}</p>'.format(variant_id, e.args)
                ),
                '[MobiDetails - MD variant class Error]'
            )
    return md_utilities.danger_panel('', 'Sorry, something went wrong with the deletion of this annotation. An admin has been warned.')

# -------------------------------------------------------------------
# web app - ajax to contact other users


@bp.route('/send_var_message', methods=['POST'])
@login_required
def send_var_message():
    if re.search(r'^\d+$', request.form['receiver_id']):
        if request.form['message'] != '' and \
                re.search(r'Query\svia\sMobiDetails\sfrom', request.form['message_object']):
            # sender = {}
            receiver = {}
            # variant = request.form['variant_mes']
            # sender['id'] = request.form['sender_id']
            receiver['id'] = request.form['receiver_id']
            message = request.form['message']
            message_object = request.form['message_object']
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # get username and email
            # curs.execute(
            #     "SELECT id, username, email FROM mobiuser WHERE id IN ('{0}', '{1}')".format(
            #             sender['id'],
            #             receiver['id']
            #         )
            # )
            curs.execute(
                "SELECT id, username, email FROM mobiuser WHERE id = %s",
                (receiver['id'])
            )
            # res = curs.fetchall()
            receiver = curs.fetchone()
            # for user in res:
            #     # print(user)
            #     if int(user['id']) == int(sender['id']):
            #         sender['username'] = user['username']
            #         sender['email'] = user['email']
            #     elif int(user['id']) == int(receiver['id']):
            #         receiver['username'] = user['username']
            #         receiver['email'] = user['email']
            message.replace("\n", "<br />")
            message += "<br /><br /><p>You can contact user {0} directly at {1}</p>".format(
                    g.user['username'],
                    g.user['email']
                )
            md_utilities.send_email(
                md_utilities.prepare_email_html(message_object, message, False),
                message_object,
                [receiver['email']]
            )
            return md_utilities.info_panel('Your email has just been sent.', '', '', 'w3-pale-green')
        else:
            return md_utilities.danger_panel('', 'Please complete the message part of the form.')
    md_utilities.send_error_email(
        md_utilities.prepare_email_html(
            'MobiDetails error',
            '<p>An email was not sent from {0} to {1}<br />Variant was {2}<br />Message was:<br />{3}</p>'.format(
                g.user['sender_id'],
                request.form['receiver_id'],
                request.form['variant_mes'],
                request.form['message'])
        ),
        '[MobiDetails - Email Error]'
    )
    return md_utilities.danger_panel('', 'Sorry, something went wrong with this message. An admin has been warned.')

# -------------------------------------------------------------------
# web app - ajax for variant creation via VV API https://rest.variantvalidator.org/webservices/variantvalidator.html


@bp.route('/create', methods=['POST'])
def create():
    # print(request.form['new_variant'])
    if request.form['new_variant'] == '':
        return md_utilities.danger_panel('variant creation attempt', 'Please fill in the form before submitting!')
    if re.search(r'^[\w-]+$', request.form['gene']) and \
            re.search(r'^NM_\d+$', request.form['acc_no']) and \
            re.search(rf'^c\.{md_utilities.variant_regexp}$', request.form['new_variant']) and \
            re.search(r'^\d+$', request.form['acc_version']):
        gene = request.form['gene']
        acc_no = request.form['acc_no']
        new_variant = request.form['new_variant']
        new_variant = new_variant.replace(" ", "")
        new_variant = new_variant.replace("\t", "")
        original_variant = new_variant
        acc_version = request.form['acc_version']
        alt_nm = None
        if 'alt_iso' in request.form:
            alt_nm = request.form['alt_iso']
            # return md_utilities.danger_panel(alt_nm, acc_version)
            if alt_nm != '' and alt_nm != "{0}.{1}".format(acc_no, acc_version):
                acc_no, acc_version = alt_nm.split('.')
        # variant already registered?
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        var_db = new_variant.replace("c.", "")
        curs.execute(
            "SELECT id FROM variant_feature WHERE c_name = %s AND gene_name[2] = %s",
            (var_db, acc_no)
        )
        res = curs.fetchone()
        if res is not None:
            close_db()
            return md_utilities.info_panel('Variant already in MobiDetails: ', var_db, res['id'])
    
        if re.search(r'c\..+', new_variant):
            # is vv alive?
            http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
            vv_alive = None
            try:
                json.loads(http.request('GET', md_utilities.urls['variant_validator_api_hello']).data.decode('utf-8'))
            except Exception as e:
                md_utilities.send_error_email(
                    md_utilities.prepare_email_html(
                        'MobiDetails VariantValidator error',
                        '<p>VariantValidator looks down!!<br /> - from {0} with args: {1}</p>'.format(
                            os.path.basename(__file__), e.args
                        )
                    ),
                    '[MobiDetails - VariantValidator Error]'
                )
                # vv_data = {'apiVersion': 'Service Unavailable'}
                vv_alive = {'status': 'Service Unavailable'}
                close_db()
                return md_utilities.danger_panel(
                    new_variant, 'Variant Validator did not answer our call, status: {}. \
                    I have been informed by email. Please retry later.'.format(vv_alive['status']))
    
            # http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
            if alt_nm is None or acc_no == request.form['acc_no']:
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}.{2}:{3}/{1}.{2}?content-type=application/json".format(
                    md_utilities.urls['variant_validator_api'], acc_no, acc_version, new_variant
                )
            else:
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}.{2}:{3}/all?content-type=application/json".format(
                    md_utilities.urls['variant_validator_api'], acc_no, acc_version, new_variant
                )
            vv_key_var = "{0}.{1}:{2}".format(acc_no, acc_version, new_variant)
            try:
                vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
            except Exception:
                close_db()
                return md_utilities.danger_panel(
                    new_variant,
                    'Variant Validator did not return any value for the variant.\
                    Either it is down or your nomenclature is very odd!'
                )
            if re.search('[di][neu][psl]', new_variant):
                # need to redefine vv_key_var for indels as the variant name returned by vv is likely to be different form the user's
                for key in vv_data:
                    if re.search('{0}.{1}'.format(acc_no, acc_version), key):
                        vv_key_var = key
                        # print(key)
                        var_obj = re.search(r':(c\..+)$', key)
                        if var_obj is not None:
                            new_variant = var_obj.group(1)
        else:
            close_db()
            return md_utilities.danger_panel(new_variant, 'Please provide the variant name as HGVS c. nomenclature (including c.)')
        print(vv_key_var)        
        return md_utilities.create_var_vv(
            vv_key_var, gene, acc_no, new_variant,
            original_variant, acc_version, vv_data,
            'webApp', db, g
        )
    else:
        close_db()
        return md_utilities.danger_panel('variant creation attempt', 'A mandatory argument is lacking or is malformed.')

# -------------------------------------------------------------------
# web app - ajax to modify email prefs for logged users


@bp.route('/toggle_email_prefs', methods=['POST'])
@login_required
def toggle_email_prefs():
    # if re.search(r'^\d+$', request.form['user_id']) and \
    #        re.search(r'^[ft]$', request.form['pref_value']):
    if re.search(r'^[ft]$', request.form['pref_value']):
        # mobiuser_id = request.form['user_id']
        email_prefs = request.form['pref_value']
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "UPDATE mobiuser SET email_pref = %s WHERE id = %s",
            (email_prefs, g.user['id'])
        )
        db.commit()
        return 'ok'

    md_utilities.send_error_email(
        md_utilities.prepare_email_html(
            'MobiDetails error',
            '<p>MD failed to modify a user email prefs. User id: {0} to {1}</p>'.format(
                g.user['id'],
                request.form['pref_value']
            )
        ),
        '[MobiDetails - Email prefs Error]'
    )
    return md_utilities.danger_panel('', 'Sorry, something went wrong when trying to update your preferences.\
                                              An admin has been warned. Please try again later.')

# -------------------------------------------------------------------
# web app - ajax to mark/unmark variants as favourite for logged users


@bp.route('/favourite', methods=['POST'])
@login_required
def favourite():
    if re.search(r'^\d+$', request.form['vf_id']):
        vf_id = request.form['vf_id']
        if vf_id is None:
            flash('Cannot mark a variant without id! Please contact us.', 'w3-pale-red')
            return 'notok'
        # print(vf_id)
        # g.user['id']
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if request.form['marker'] == 'mark':
            curs.execute(
                "INSERT INTO mobiuser_favourite (mobiuser_id, feature_id) VALUES (%s, %s)",
                (g.user['id'], vf_id)
            )
        else:
            curs.execute(
                "DELETE FROM mobiuser_favourite WHERE mobiuser_id = %s AND feature_id = %s",
                (g.user['id'], vf_id )
            )
        db.commit()
        close_db()
        return 'ok'
    else:
        flash('Cannot mark a variant without id! Please contact us.', 'w3-pale-red')
        return 'notok'

# -------------------------------------------------------------------
# web app - ajax for search engine autocomplete


@bp.route('/autocomplete', methods=['POST'])
def autocomplete():
    query = request.form['query_engine']
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # match_object = re.search(r'^c\.([\w\d>_\*-]+)', query)
    match_object = re.search(rf'^c\.({md_utilities.variant_regexp})', query)
    if match_object:
        md_query = match_object.group(1)
        curs.execute(
            "SELECT c_name FROM variant_feature WHERE c_name LIKE '{}%' ORDER BY c_name LIMIT 10".format(md_query)
        )
        res = curs.fetchall()
        result = []
        for var in res:
            result.append('c.{}'.format(var[0]))
        # print(json.dumps(result))
        # print("SELECT c_name FROM variant_feature WHERE gene_name[1] = '{0}' AND c_name LIKE '{1}%' ORDER BY c_name LIMIT 10".format(gene, md_query))
        if result is not None:
            return json.dumps(result)
        else:
            return ('', 204)
    i = 1
    if re.search(r'^[Nn][Mm]_.+', query):
        i = 2
        query = query.upper()
    elif not re.search(r'orf', query):
        query = query.upper()
    curs.execute(
        "SELECT DISTINCT name[1] FROM gene WHERE name[{0}] LIKE '%{1}%' ORDER BY name[1] LIMIT 5".format(i, query)
    )
    res = curs.fetchall()
    result = []
    for gene in res:
        result.append(gene[0])
    # print("SELECT DISTINCT name[1] FROM gene WHERE name[{0}] LIKE '%{1}%' ORDER BY name[1] LIMIT 5".format(i, query))
    if result is not None:
        return json.dumps(result)
    else:
        return ('', 204)

# -------------------------------------------------------------------
# web app - ajax for variant creation autocomplete


@bp.route('/autocomplete_var', methods=['POST'])
def autocomplete_var():
    query = request.form['query_engine']
    gene = request.form['gene']
    # match_object = re.search(r'^c\.([\w\d>_\*-]+)', query)
    match_object = re.search(rf'^c\.({md_utilities.variant_regexp})', query)
    if match_object:
        md_query = match_object.group(1)
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT c_name FROM variant_feature WHERE gene_name[1] = '{0}' AND c_name LIKE '{1}%' ORDER BY c_name LIMIT 10".format(
                gene, md_query
            )
        )
        res = curs.fetchall()
        result = []
        for var in res:
            result.append('c.{}'.format(var[0]))
        # print(json.dumps(result))
        # print("SELECT c_name FROM variant_feature WHERE gene_name[1] = '{0}' AND c_name LIKE '{1}%' ORDER BY c_name LIMIT 10".format(gene, md_query))
        if result is not None:
            return json.dumps(result)
        else:
            return ('', 204)
    return ('', 204)
