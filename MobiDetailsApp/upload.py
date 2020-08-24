import os
import re
import urllib3
import certifi
import urllib.parse
import psycopg2
import psycopg2.extras
import json
from flask import Blueprint, request, redirect, current_app, render_template, flash, g, url_for
from werkzeug.utils import secure_filename
from MobiDetailsApp.db import get_db, close_db
from . import (
    config, md_utilities
)

bp = Blueprint('upload', __name__)

# adapted from https://pythonise.com/series/learning-flask/flask-uploading-files

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    # if not "." in filename:
    #     return False
    # ext = filename.rsplit(".", 1)[1]
    # if ext.lower() in current_app.config['ALLOWED_EXTENSIONS']:
    #     return True
    # else:
    #     return False


# def allowed_filesize(filesize):
#     if int(filesize) <= current_app.config["MAX_CONTENT_LENGTH"]:
#         return True
#     else:
#         return False


@bp.route('/file_upload', methods=['GET', 'POST'])
def file_upload():
    if request.method == 'POST':
        if request.files:
            uploaded_file = request.files['file']
            if uploaded_file.filename == "":
                flash('No filename.', 'w3-pale-red')
                return redirect(request.url)
            if allowed_file(uploaded_file.filename):
                filename = secure_filename(uploaded_file.filename)
                lines = uploaded_file.read().decode().replace('\r\n', '\n').replace('\r', '\n').split('\n')
                # print(lines)
                # ok we've got the file
                # get user API key or use MD
                db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                #headers
                header = {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36',
                }
                result = []
                api_key = None
                if g.user:                    
                    curs.execute(
                        "SELECT api_key FROM mobiuser WHERE id = %s",
                        (g.user['id'],)
                    )
                    res_key = curs.fetchone()
                    if res_key:
                        api_key = res_key['api_key']
                else:
                    curs.execute(
                        "SELECT api_key FROM mobiuser WHERE username = 'mobidetails'"
                    )
                    res_key = curs.fetchone()
                    if res_key:
                        api_key = res_key['api_key']
                if api_key is None:
                    flash('There is an issue in obtaining an API key')
                    return redirect(request.url)
                # we need to check the format and send a proper query to the API
                for line in lines:
                    # print('-{}-'.format(line))
                    # cDNA format
                    md_response = []
                    match_obj_c = re.search(rf'^(NM_\d+)\.(\d+):(c\.{md_utilities.variant_regexp})$', line)                   
                    if match_obj_c:
                        # check NM number and version
                        curs.execute(
                            "SELECT nm_version FROM gene WHERE name[2] = %s",
                            (match_obj_c.group(1),)
                        )
                        res_nm = curs.fetchone()
                        if res_nm:
                            # send var to api
                            md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_create'))
                            # md_api_url = '{0}/api/variant/create'.format(md_api_base_url)
                            # print(md_api_url)
                            data = {
                                'variant_chgvs': urllib.parse.quote('{0}.{1}:{2}'.format(match_obj_c.group(1), match_obj_c.group(2), match_obj_c.group(3))),
                                'api_key': api_key
                            }            
                            try:
                                md_response = json.loads(http.request('POST', md_api_url, headers=header, fields=data).data.decode('utf-8'))
                                print(md_response)
                                result.append({'variant': line, 'id': md_response['mobidetails_id'], 'url': md_response['url']})
                            except Exception:
                                if 'mobidetails_error' in md_response:
                                    result.append({'variant': line, 'error': md_response['mobidetails_error']})
                                else:
                                    result.append({'variant': line, 'error': 'MDAPI call failed'})
                        else:
                            result.append({'variant': line, 'error': 'Unknown NCBI NM accession number'})
                        continue
                    # genomic format
                    match_obj_g = re.search(rf'^(NC_\d+\.\d+:g\.{md_utilities.variant_regexp});([\w-]+)$', line)
                    if match_obj_g:
                        # check NM number and version
                        curs.execute(
                            "SELECT nm_version FROM gene WHERE name[1] = %s",
                            (match_obj_g.group(2),)
                        )
                        res_nm = curs.fetchone()
                        if res_nm:
                            # send var to api
                            md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_g_create'))
                            # print(md_api_url)
                            data = {
                                'variant_ghgvs': urllib.parse.quote(match_obj_g.group(1)),
                                'gene_hgnc': match_obj_g.group(2),
                                'caller': 'cli',
                                'api_key': api_key
                            }            
                            try:
                                md_response = json.loads(http.request('POST', md_api_url, headers=header, fields=data).data.decode('utf-8'))
                                # print(md_response)
                                result.append({'variant': line, 'id': md_response['mobidetails_id']})
                            except Exception:                                
                                if 'variant_validator_output' in md_response and \
                                        'validation_warning_1' in md_response['variant_validator_output'] and \
                                        'validation_warnings' in md_response['variant_validator_output']['validation_warning_1']:
                                    result.append({'variant': line, 'error': md_response['variant_validator_output']['validation_warning_1']['validation_warnings'][0]})
                                elif 'mobidetails_error' in md_response:
                                    result.append({'variant': line, 'error': md_response['mobidetails_error']})
                                    v
                                else:
                                    result.append({'variant': line, 'error': 'MDAPI call failed'})
                        else:
                            result.append({'variant': line, 'error': 'Unknown gene'})
                        continue
                    result.append({'variant': line, 'error': 'Bad format'})
                flash('File correctly uploaded', 'w3-pale-green')
                return render_template('md/variant_multiple.html', upload=result)
            else:
                flash('That file extension is not allowed', 'w3-pale-red')
                return redirect(request.url)

    return render_template("upload/upload_form.html")
