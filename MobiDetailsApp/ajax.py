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
            return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%;">The Litvar query failed</div>'
        if litvar_data is not None:
            # if len(litvar_data) == 0: or re.search(r'mandatory', litvar_data[0])
            if len(litvar_data) == 0:
                return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%;">No match in Pubmed using LitVar API</div>'
            pubmed_info = {}
            togows_url = '{0}/entry/ncbi-pubmed/'.format(md_utilities.urls['togows'])
            for pubmed_id in litvar_data[0]['pmids']:
                togows_url = '{0}{1},'.format(togows_url, pubmed_id)
            togows_url = '{0}.json'.format(togows_url[:-1])
            # print(togows_url)
            try:
                pubmeds = json.loads(http.request('GET', togows_url).data.decode('utf-8'))
                for article in pubmeds:
                    # print(article)
                    if article['authors'][0]:
                        pmid = int(article['pmid'])
                        pubmed_info[pmid] = {}
                        pubmed_info[pmid]['title'] = article['title']
                        pubmed_info[pmid]['journal'] = article['journal']
                        pubmed_info[pmid]['year'] = article['year']
                        pubmed_info[pmid]['author'] = article['authors'][0]
            except Exception:
                for pubmed_id in litvar_data[0]['pmids']:
                    pmid = int(pubmed_id)
                    pubmed_info[pmid] = {}
                    pubmed_info[pmid]['title'] = ''
            return render_template('ajax/litvar.html', urls=md_utilities.urls, pmids=pubmed_info)
            # return render_template('ajax/litvar.html', urls=md_utilities.urls, pmids=litvar_data[0]['pmids'])
        else:
            return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%;">No match in Pubmed using LitVar API</div>'
    else:
        return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%;">No match in Pubmed using LitVar API</div>'

######################################################################
# web app - ajax for defgen export file


@bp.route('/defgen', methods=['POST'])
def defgen():
    genome_regexp = md_utilities.regexp['genome']
    match_obj = re.search(rf'^({genome_regexp})$', request.form['genome'])
    if re.search(r'^\d+$', request.form['vfid']) and \
            match_obj:
            # re.search(rf'^{genome_regexp}$', request.form['genome']):
        variant_id = request.form['vfid']
        # genome = request.form['genome']
        genome = match_obj.group(1)
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

        file_content += "{0};{1}.{2}:c.{3};;;;p.{4};c.{3};{5};{1}.{2};{6};;;;rs{7};;{8};;chr{9};{10};chr{9}:g.{11};{12} {13};;;;\r\n".format(
            vf['gene_name'][0], vf['gene_name'][1], vf['nm_version'], vf['c_name'], vf['p_name'], vf['enst'], vf['pos'],
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
        # close_db()
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
    genome_regexp = md_utilities.regexp['genome']
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    if re.search(rf'^{genome_regexp}$', request.form['genome']) and \
            re.search(rf'^{nochr_chrom_regexp}$', request.form['chrom']) and \
            re.search(r'^\d+$', request.form['pos']) and \
            re.search(r'^[ATGC]+$', request.form['ref']) and \
            re.search(r'^[ATGC]+$', request.form['alt']) and \
            'gene' in request.form:
        genome = request.form['genome']
        chrom = request.form['chrom']
        pos = request.form['pos']
        ref = request.form['ref']
        alt = request.form['alt']
        gene = request.form['gene']
        if len(ref) > 1 or len(alt) > 1:
            return 'No wintervar for indels'
        if ref == alt:
            return 'hg19 reference is equal to variant: no wIntervar query'
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        intervar_url = "{0}{1}_updated.v.201904&chr={2}&pos={3}&ref={4}&alt={5}".format(
            md_utilities.urls['intervar_api'], genome, chrom,
            pos, ref, alt
        )
        # print(intervar_url)
        try:
            intervar_data = [json.loads(http.request('GET', intervar_url).data.decode('utf-8'))]
        except Exception:
            try:
                # intervar can return mutliple json objects, e.g.:
                # {"Intervar":"Uncertain significance","Chromosome":1,"Position_hg19":151141512,"Ref_allele":"T","Alt_allele":"A","Gene":"SCNM1","PVS1":0,"PS1":0,"PS2":0,"PS3":0,"PS4":0,"PM1":1,"PM2":1,"PM3":0,"PM4":0,"PM5":0,"PM6":0,"PP1":0,"PP2":0,"PP3":0,"PP4":0,"PP5":0,"BA1":0,"BP1":0,"BP2":0,"BP3":0,"BP4":0,"BP5":0,"BP6":0,"BP7":0,"BS1":0,"BS2":0,"BS3":0,"BS4":0}{"Intervar":"Uncertain significance","Chromosome":1,"Position_hg19":151141512,"Ref_allele":"T","Alt_allele":"A","Gene":"TNFAIP8L2-SCNM1","PVS1":0,"PS1":0,"PS2":0,"PS3":0,"PS4":0,"PM1":1,"PM2":1,"PM3":0,"PM4":0,"PM5":0,"PM6":0,"PP1":0,"PP2":0,"PP3":0,"PP4":0,"PP5":0,"BA1":0,"BP1":0,"BP2":0,"BP3":0,"BP4":0,"BP5":0,"BP6":0,"BP7":0,"BS1":0,"BS2":0,"BS3":0,"BS4":0}
                intervar_list = re.split('}{', http.request('GET', intervar_url).data.decode('utf-8'))
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
                        '<p>Intervar API call failed for {0}-{1}-{2}-{3}-{4} - url: {5} <br /> - from {6} with args: {7}</p>'.format(
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
                        # intervar_criteria = str(intervar_criteria) + '<li>{0}: {1}</li>'.format(key, md_utilities.acmg_criteria[key])
                        # intervar_criteria = str(intervar_criteria) + '<li onmouseover="$(\'#{0}acmg_info\').css(\'display\', \'inline\');" onmouseout="$(\'#{0}acmg_info\').css(\'display\', \'none\');"><span class="{1}">{0}</span><span id="{0}acmg_info" style="display:none" >: {2}</span></li>'.format(key, md_utilities.get_acmg_criterion_color(key), md_utilities.acmg_criteria[key])
                        intervar_criteria = str(intervar_criteria) + '&nbsp;<div class="w3-col {0} w3-opacity-min w3-hover-shadow" style="width:50px;" onmouseover="$(\'#acmg_info\').text(\'{1}: {2}\');">{1}</div>'.format(md_utilities.get_acmg_criterion_color(key), key, md_utilities.acmg_criteria[key])
            except Exception:
                # md_utilities.send_error_email(
                #     md_utilities.prepare_email_html(
                #         'MobiDetails API error',
                #         '<p>Intervar API call failed for {0}-{1}-{2}-{3}-{4}<br /> - from {5} with args: A mandatory argument is missing</p>'.format(
                #             request.form['genome'], request.form['chrom'],
                #             request.form['pos'], request.form['ref'],
                #             request.form['alt'], os.path.basename(__file__)
                #         )
                #     ),
                #     '[MobiDetails - API Error]'
                # )
                return "<span>wintervar looks down</span>"            
        else:
            for intervar_dict in intervar_data:
                # intervar likely returns several json objects
                if intervar_dict['Gene'] == gene:
                    intervar_acmg = intervar_dict['Intervar']
                    for key in intervar_dict:
                        if key != 'Chromosome' and \
                                intervar_dict[key] == 1:
                            # intervar_criteria = str(intervar_criteria) + '<li>{0}: {1}</li>'.format(key, md_utilities.acmg_criteria[key])
                            # intervar_criteria = str(intervar_criteria) + '<li onmouseover="$(\'#{0}acmg_info\').css(\'display\', \'inline\');" onmouseout="$(\'#{0}acmg_info\').css(\'display\', \'none\');"><span class="{1}">{0}</span><span id="{0}acmg_info" style="display:none" >: {2}</span></li>'.format(key, md_utilities.get_acmg_criterion_color(key), md_utilities.acmg_criteria[key])
                            intervar_criteria = str(intervar_criteria) + '<div class="w3-col {0} w3-opacity-min w3-hover-shadow" style="width:50px;" onmouseover="$(\'#acmg_info\').text(\'{1}: {2}\');">{1}</div>'.format(md_utilities.get_acmg_criterion_color(key), key, md_utilities.acmg_criteria[key])
        if intervar_acmg is not None:
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                "SELECT html_code FROM valid_class WHERE acmg_translation = '{}'".format(
                    intervar_acmg.lower()
                )
            )
            res = curs.fetchone()
            close_db()
            return "<span style='color:{0};'>{1}</span><span> with the following criteria:</span><br /><br /><div class='w3-row-padding w3-center'>{2}</div><br /><div id='acmg_info'></div>".format(res['html_code'], intervar_acmg, intervar_criteria)
        else:
            return "<span>No wintervar class</span>"
    else:
        md_utilities.send_error_email(
            md_utilities.prepare_email_html(
                'MobiDetails API error',
                '<p>Intervar API call failed for {0}-{1}-{2}-{3}-{4}<br /> - from {5} with args: A mandatory argument is missing</p>'.format(
                    request.form['genome'], request.form['chrom'],
                    request.form['pos'], request.form['ref'],
                    request.form['alt'], os.path.basename(__file__)
                )
            ),
            '[MobiDetails - API Error]'
        )
        return "<span>Bad request</span>"

# -------------------------------------------------------------------
# web app - ajax for LOVD API


@bp.route('/lovd', methods=['POST'])
def lovd():
    genome = chrom = g_name = c_name = gene = None
    genome_regexp = md_utilities.regexp['genome']
    nochr_chrom_regexp = md_utilities.regexp['nochr_chrom']
    variant_regexp = md_utilities.regexp['variant']
    # print(request.form)
    if re.search(rf'^{genome_regexp}$', request.form['genome']) and \
            re.search(rf'^{nochr_chrom_regexp}$', request.form['chrom']) and \
            re.search(rf'^{variant_regexp}$', request.form['g_name']) and \
            re.search(rf'^c\.{variant_regexp}$', request.form['c_name']) and \
            'gene' in request.form:
        # and \
        #    'pos' in request.form:
        genome = request.form['genome']
        chrom = request.form['chrom']
        g_name = request.form['g_name']
        c_name = request.form['c_name']
        gene = request.form['gene']
        # pos_19 = request.form['pos']
        if re.search(r'=', g_name):
            return md_utilities.lovd_error_html("hg19 reference is equal to variant: no LOVD query")
            # return 'hg19 reference is equal to variant: no LOVD query'
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
            lovd_effect_count = None
            if len(lovd_data) == 1:
                return md_utilities.lovd_error_html("No match in LOVD public instances")
                # return 'No match in LOVD public instances'
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
                            lovd_fh = open(md_utilities.local_files['lovd_ref']['abs_path'])
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
                        html_list.append("{0}<a href='{1}' target='_blank'>{2} </a>{3}".format(html_li, url, lovd_name, html_li_end))
                    else:
                        html_list.append("{0}<a href='{1}' target='_blank'>Link {2} </a>{3}".format(html_li, url, i, html_li_end))
                    i += 1
                # get LOVD effects e.g.
                # https://databases.lovd.nl/shared/api/rest/variants/USH2A?search_position=g.216420460&show_variant_effect=1&format=application/json
                lovd_api_url = '{0}{1}?search_position=g.{2}&show_variant_effect=1&format=application/json'.format(
                    md_utilities.urls['lovd_api_variants'], gene, positions[0]
                )
                lovd_effect = None
                try:
                    lovd_effect = json.loads(http.request('GET', lovd_api_url).data.decode('utf-8'))
                except Exception:
                    pass
                if lovd_effect is not None and \
                        len(lovd_effect) != 0:
                    # print(lovd_effect)
                    lovd_effect_count = {
                        'effect_reported': {},
                        'effect_concluded': {}
                    }
                    for var in lovd_effect:
                        if var['effect_reported'][0] not in lovd_effect_count['effect_reported']:
                            lovd_effect_count['effect_reported'][var['effect_reported'][0]] = 1
                        else:
                            lovd_effect_count['effect_reported'][var['effect_reported'][0]] += 1
                        if var['effect_concluded'][0] not in lovd_effect_count['effect_concluded']:
                            lovd_effect_count['effect_concluded'][var['effect_concluded'][0]] = 1
                        else:
                            lovd_effect_count['effect_concluded'][var['effect_concluded'][0]] += 1
                # print(lovd_effect_count)

            else:
                return md_utilities.lovd_error_html("No match in LOVD public instances")
                # return 'No match in LOVD public instances'
            html = '<tr><td class="w3-left-align" id="lovd_feature" style="vertical-align:middle;">LOVD Matches:</td> \
                   <td class="w3-left-align"><ul>{}</ul></td> \
                   <td class="w3-left-align" id="lovd_description" style="vertical-align:middle;"> \
                   <em class="w3-small">LOVD match in public instances</em></td> \
                   </tr>'.format(''.join(html_list))
            if lovd_effect_count is not None:
                reported_effect_list = []
                concluded_effect_list = []
                for feat in lovd_effect_count:
                    # print(feat)
                    for effect in lovd_effect_count[feat]:
                        # print(effect)
                        if feat == 'effect_reported':
                            reported_effect_list.append('<div class="w3-col w3-{0} w3-opacity-min w3-padding w3-margin-top w3-margin-left w3-hover-shadow" style="width:180px;">{1}: {2}  </div>'.format(md_utilities.lovd_effect[effect]['color'], md_utilities.lovd_effect[effect]['translation'], lovd_effect_count[feat][effect]))
                            # reported_effect_list.append('<li>{0}: {1} </li>'.format(effect, lovd_effect_count[feat][effect]))
                        else:
                            concluded_effect_list.append('<div class="w3-col w3-{0} w3-opacity-min w3-padding w3-margin-top w3-margin-left w3-hover-shadow" style="width:180px;">{1}: {2}  </div>'.format(md_utilities.lovd_effect[effect]['color'], md_utilities.lovd_effect[effect]['translation'], lovd_effect_count[feat][effect]))
                            # concluded_effect_list.append('<li>{0}: {1} </li>'.format(effect, lovd_effect_count[feat][effect]))
                html += ',<tr> \
                   <td class="w3-left-align" id="lovd_r_feature" style="vertical-align:middle;">LOVD Effect Reported:</td> \
                   <td class="w3-center" style="vertical-align:middle;"><div class="w3-row w3-center">{0}</div><br /></td> \
                   <td class="w3-left-align" id="lovd_r_feature" style="vertical-align:middle;"> \
                   <em class="w3-small">Effects reported by LOVD submitters</em></td> \
                   </tr>,<tr> \
                   <td class="w3-left-align" id="lovd_c_description" style="vertical-align:middle;">LOVD Effect Concluded:</td> \
                   <td class="w3-center" style="vertical-align:middle;"><div class="w3-row w3-center">{1}</div><br /></td>\
                   <td class="w3-left-align" id="lovd_c_description" style="vertical-align:middle;"> \
                   <em class="w3-small">Effects concluded by LOVD curators</em></td> \
                   </tr>'.format(''.join(reported_effect_list), ''.join(concluded_effect_list))
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
                '<p>LOVD API call failed in {0} with args: a mandatory argument is missing</p>'.format(
                    os.path.basename(__file__)
                )
            ),
            '[MobiDetails - API Error]'
        )
        return md_utilities.lovd_error_html("LOVD query malformed")
    # return "<span>{0}</span><span>{1}</span>".format(lovd_data, lovd_url)

# -------------------------------------------------------------------
# web app - ajax for ACMG classification modification


@bp.route('/modif_class', methods=['POST'])
@login_required
def modif_class():
    # tr_html = 'notok'
    if 'variant_id' in request.form and \
            re.search(r'^\d+$', request.form['variant_id']) and \
            'acmg_select' in request.form and \
            re.search(r'^\d+$', request.form['acmg_select']) and \
            'acmg_comment' in request.form:
        variant_id = request.form['variant_id']
        acmg_select = request.form['acmg_select']
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
                "SELECT class_date FROM class_history WHERE \
                    variant_feature_id = %s AND acmg_class = %s \
                    AND mobiuser_id = %s",
                (variant_id, acmg_select, g.user['id'])
            )
            res = curs.fetchone()
            if res:
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
                # if first classification and current owner == mobidetails => user become owner
                curs.execute(
                    "SELECT acmg_class FROM class_history WHERE \
                        variant_feature_id = %s",
                    (variant_id,)
                )
                res_acmg = curs.fetchone()
                # print("res_amcg: {}".format(res_acmg))
                if not res_acmg:
                    semaph = 1
                    curs.execute(
                        "SELECT creation_user FROM variant_feature WHERE id = %s",
                        (variant_id,)
                    )
                    res_user = curs.fetchone()
                    # print("res_user_id: {}".format(res_user['creation_user']))
                    # get mobidetails user id
                    mobidetails_id = md_utilities.get_user_id('mobidetails', db)
                    if res_user and \
                            res_user['creation_user'] == mobidetails_id:
                        curs.execute(
                            "UPDATE variant_feature SET creation_user = %s WHERE id = %s",
                            (g.user['id'], variant_id)
                        )
                curs.execute(
                    "INSERT INTO class_history (variant_feature_id, acmg_class, mobiuser_id, class_date, comment) VALUES \
                        (%s, %s, %s, %s, %s )",
                    (variant_id, acmg_select, g.user['id'], date, acmg_comment)
                )
            db.commit()
            curs.execute(
                "SELECT html_code, acmg_translation, lovd_translation FROM valid_class WHERE acmg_class = %s",
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
            # Send data to LOVD if relevant
            ########### REPLACE md_utilities.host['dev'] with md_utilities.host['prod'] WHEN LOVD FEATURE IS READY ###########
            if g.user['lovd_export'] is True and \
                    url_parse(request.referrer).host == md_utilities.host['prod']:
                with open(md_utilities.local_files['lovd_api_json']['abs_path']) as json_file:
                    lovd_json = json.load(json_file)
                # get HGVS genomic, cDNA, protein HGNC gene name and refseq acc version
                genome_version = 'hg19'
                curs.execute(
                    "SELECT a.c_name, a.gene_name, a.p_name, a.dbsnp_id, b.g_name, d.hgnc_id, c.ncbi_name, d.nm_version FROM variant_feature a, variant b, chromosomes c, gene d WHERE \
                    a.id = b.feature_id AND b.genome_version = c.genome_version AND b.chr = c.name \
                    AND a.gene_name = d.name AND a.id = %s AND b.genome_version = %s",
                    (variant_id, genome_version)
                )
                res_var = curs.fetchone()
                lovd_json['lsdb']['variant'][0]['ref_seq']['@accession'] = res_var['ncbi_name']
                lovd_json['lsdb']['variant'][0]['name']['#text'] = 'g.{}'.format(res_var['g_name'])

                if res_var['dbsnp_id']:
                    lovd_json['lsdb']['variant'][0]['db_xref'][0]['@accession'] = 'rs{}'.format(res_var['dbsnp_id'])                    
                else:
                    lovd_json['lsdb']['variant'][0].pop('db_xref', None)
                if res_var['hgnc_id'] == 0:
                    lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['gene']['@accession'] = res_var['gene_name'][0]
                else:
                    lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['gene']['@accession'] = res_var['hgnc_id']
                lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['ref_seq']['@accession'] = '{0}.{1}'.format(res_var['gene_name'][1], res_var['nm_version'])
                lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['name']['#text'] = 'c.{}'.format(res_var['c_name'])
                lovd_json['lsdb']['variant'][0]['seq_changes']['variant'][0]['seq_changes']['variant'][0]['name']['#text'] = 'p.({})'.format(res_var['p_name'])
                if semaph == 1:
                    # first time submission
                    lovd_json['lsdb']['variant'][0]['pathogenicity']['@term'] = acmg_details['lovd_translation']
                else:                
                    # build ACMG class for LOVD update
                    curs.execute(
                        "SELECT acmg_class FROM class_history WHERE \
                            variant_feature_id = %s",
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
                http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                # headers
                header = md_utilities.api_agent
                header['Content-Type'] = 'application/json'
                try:
                    lovd_response = http.request('POST', md_utilities.urls['lovd_api_submissions'], body=json.dumps(lovd_json).encode('utf-8'), headers=header).data.decode('utf-8')
                    print('LOVD submission for {0}:g.{1} : {2}'.format(res_var['ncbi_name'], res_var['g_name'], lovd_response))
                except Exception:
                    pass                
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
            curs.execute(
                "SELECT id, username, email FROM mobiuser WHERE id = %s",
                (receiver['id'])
            )
            # res = curs.fetchall()
            receiver = curs.fetchone()
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
    # start_time = time.time()
    # print(request.form['new_variant'])
    variant_regexp = md_utilities.regexp['variant']
    if request.form['new_variant'] == '':
        return md_utilities.danger_panel('variant creation attempt', 'Please fill in the form before submitting!')
    if re.search(r'^[\w-]+$', request.form['gene']) and \
            re.search(r'^NM_\d+$', request.form['acc_no']) and \
            re.search(rf'^c\.{variant_regexp}$', request.form['new_variant']) and \
            re.search(r'^\d+$', request.form['acc_version']):
        gene = request.form['gene']
        acc_no = request.form['acc_no']
        new_variant = request.form['new_variant']
        new_variant = new_variant.replace(" ", "").replace("\t", "")
        # new_variant = new_variant.replace("\t", "")
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
        if res:
            close_db()
            return md_utilities.info_panel('Variant already in MobiDetails: ', var_db, res['id'])

        if re.search(r'c\..+', new_variant):
            # is vv alive?
            
            # vv_alive = None
            vv_base_url = md_utilities.get_vv_api_url()
            # try:
            #     json.loads(http.request('GET', md_utilities.urls['variant_validator_api_hello']).data.decode('utf-8'))
            # except Exception as e:
            #     try:
            #         json.loads(http.request('GET', md_utilities.urls['variant_validator_api_hello_backup']).data.decode('utf-8'))
            #         vv_base_url = md_utilities.urls['variant_validator_api_backup']
            #     except Exception as e:
            #         md_utilities.send_error_email(
            #             md_utilities.prepare_email_html(
            #                 'MobiDetails VariantValidator error',
            #                 '<p>VariantValidator looks down!!<br /> - from {0} with args: {1}</p>'.format(
            #                     os.path.basename(__file__), e.args
            #                 )
            #             ),
            #             '[MobiDetails - VariantValidator Error]'
            #         )
            #         # vv_data = {'apiVersion': 'Service Unavailable'}
            #         # vv_alive = {'status': 'Service Unavailable'}
            if not vv_base_url:
                close_db()
                return md_utilities.danger_panel(
                        new_variant, 'Variant Validator did not answer our call, status: Service Unavailable. \
                        I have been informed by email. Please retry later.')

            # http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
            if not alt_nm or acc_no == request.form['acc_no']:
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}.{2}:{3}/{1}.{2}?content-type=application/json".format(
                    vv_base_url, acc_no, acc_version, new_variant
                )
            else:
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}.{2}:{3}/all?content-type=application/json".format(
                    vv_base_url, acc_no, acc_version, new_variant
                )
            vv_key_var = "{0}.{1}:{2}".format(acc_no, acc_version, new_variant)
            try:
                http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
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
                        if var_obj:
                            new_variant = var_obj.group(1)
        else:
            close_db()
            return md_utilities.danger_panel(new_variant, 'Please provide the variant name as HGVS c. nomenclature (including c.)')
        return md_utilities.create_var_vv(
            vv_key_var, gene, acc_no, new_variant,
            original_variant, acc_version,
            vv_data, 'webApp', db, g
        )
    else:
        close_db()
        return md_utilities.danger_panel('variant creation attempt', 'A mandatory argument is lacking or is malformed.')

# -------------------------------------------------------------------
# web app - ajax to modify email prefs for logged users


@bp.route('/toggle_prefs', methods=['POST'])
@login_required
def toggle_prefs():
    # if re.search(r'^\d+$', request.form['user_id']) and \
    #        re.search(r'^[ft]$', request.form['pref_value']):
    if re.search(r'^[ft]$', request.form['pref_value']) and \
            re.search(r'^(email_pref|lovd_export)$', request.form['field']):
        # mobiuser_id = request.form['user_id']
        pref = request.form['pref_value']
        field = request.form['field']
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "UPDATE mobiuser SET {0} = '{1}' WHERE id = '{2}'".format(field, pref, g.user['id'])
        )
        db.commit()
        return 'ok'

    md_utilities.send_error_email(
        md_utilities.prepare_email_html(
            'MobiDetails error',
            '<p>MD failed to modify a user prefs for {0}. User id: {1} to {2}</p>'.format(
                request.form['field'],
                g.user['id'],
                request.form['pref_value']
            )
        ),
        '[MobiDetails - User prefs Error]'
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
                (g.user['id'], vf_id)
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
    match_obj = re.search(rf'^rs(\d+)$', query)
    if match_obj:
        md_query = match_obj.group(1)
        curs.execute(
            "SELECT dbsnp_id FROM variant_feature WHERE dbsnp_id LIKE '{}%' ORDER BY dbsnp_id LIMIT 10".format(md_query)
        )
        res = curs.fetchall()
        result = []
        for var in res:
            result.append('rs{}'.format(var[0]))
        if result is not None:
            return json.dumps(result)
        else:
            return ('', 204)
    variant_regexp = md_utilities.regexp['variant']
    match_object = re.search(rf'^c\.({variant_regexp})', query)
    if match_object:
        md_query = match_object.group(1)
        curs.execute(
            "SELECT DISTINCT(a.c_name) as name, a.gene_name[2] as gene_name, b.nm_version FROM variant_feature a, gene b WHERE a.gene_name = b.name AND a.c_name LIKE '{}%' ORDER BY c_name LIMIT 10".format(md_query)
        )
        res = curs.fetchall()
        result = []
        for var in res:
            result.append('{0}.{1}:c.{2}'.format(var['gene_name'], var['nm_version'], var['name']))
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
    variant_regexp = md_utilities.regexp['variant']
    match_object = re.search(rf'^c\.({variant_regexp})', query)
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

# -------------------------------------------------------------------
# web app - ajax to serahc for panelapp entry


@bp.route('/is_panelapp_entity', methods=['POST'])
def is_panelapp_entity():
    if 'gene_symbol' in request.form:
        gene_symbol = request.form['gene_symbol']
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        panelapp = json.loads(
                        http.request(
                            'GET',
                            '{0}genes/{1}/'.format(
                                md_utilities.urls['panelapp_api'],
                                gene_symbol)
                        ).data.decode('utf-8')
                    )
        # panelapp = None
        md_utilities.urls['panel_app'] = None
        if panelapp is not None and \
                str(panelapp['count']) != '0':
            # we can propose the link
            # panelapp_entity_url = '{0}panels/entities/{1}'.format(md_utilities.urls['panelapp'], main['name'][0])
            return '<span class="w3-button" onclick="window.open(\'{0}\', \'_blank\')">PanelApp</span>'.format('{0}panels/entities/{1}'.format(md_utilities.urls['panelapp'], gene_symbol))
        else:
            return '<span class="w3-padding">No entry in panelApp for this gene</span>'
    else:
        return '<span class="w3-padding">Unable to perform the PanelApp query</span>'


