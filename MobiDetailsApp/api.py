import re
import os
from flask import (
    Blueprint, g, request, url_for, jsonify, redirect, flash, render_template
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
# create a poolmanager
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
# -------------------------------------------------------------------
# api - check APi key


@bp.route('/api/service/check_api_key', methods=['POST'])
def check_api_key(api_key=None):
    api_key = md_utilities.get_post_param(request, 'api_key')
    # if request.args.get('api_key'):
    #     api_key = request.args.get('api_key', type=str)
    # elif 'api_key' in request.form:
    #     api_key = request.form['api_key']
    if not api_key:
        return jsonify(
            mobidetails_error='I cannot fetch the right parameters',
            api_key_pass_check=False,
            api_key_status='irrelevant'
        )
    db = get_db()
    response = md_utilities.check_api_key(db, api_key)
    if 'mobiuser' in response:
        if response['mobiuser']['activated'] is True:
            return jsonify(api_key_submitted=api_key, api_key_pass_check=True, api_key_status='active')
        return jsonify(api_key_submitted=api_key, api_key_pass_check=True, api_key_status='inactive')
    return jsonify(api_key_submitted=api_key, api_key_pass_check=False, api_key_status='irrelevant')

# -------------------------------------------------------------------
# api - check which VV is running


@bp.route('/api/service/vv_instance', methods=['GET'])
def check_vv_instance():
    vv_url = md_utilities.get_vv_api_url()
    if not vv_url:
        return jsonify(
            variant_validator_instance='No VV running',
            URL='None'
        )
    else:
        if vv_url == md_utilities.urls['variant_validator_api_backup']:
            return jsonify(
                variant_validator_instance='Running our own emergency VV server',
                URL=vv_url
            )
        elif vv_url == md_utilities.urls['variant_validator_api']:
            return jsonify(
                variant_validator_instance='Running genuine VV server',
                URL=vv_url
            )


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
            return jsonify(
                mobidetails_id=res['feature_id'],
                url='{0}{1}'.format(
                    request.host_url[:-1],
                    url_for(
                        'api.variant',
                        variant_id=res['feature_id'],
                        caller='browser'
                    )
                )
            )
        else:
            return jsonify(mobidetails_warning='The variant {} does not exist yet in MD'.format(variant_ghgvs))
    else:
        return jsonify(mobidetails_error='Malformed query {}'.format(variant_ghgvs))

# -------------------------------------------------------------------
# api - variant


@bp.route('/api/variant/<int:variant_id>/<string:caller>/', methods=['GET'])
@bp.route('/api/variant/<int:variant_id>/<string:caller>/<string:api_key>', methods=['GET'])
def variant(variant_id=None, caller='browser', api_key=None):
    if variant_id is None:
        return jsonify(mobidetails_error='No variant submitted')
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # dealing with academic or not user
    academic = True
    # typically calling from API - swagger sends ','
    if api_key and \
            api_key != ',':
        res_check_api_key = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in res_check_api_key:
            if caller != 'browser':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        academic = res_check_api_key['mobiuser']['academic']
    # typically calling from webapp
    elif g.user:
        curs.execute(
            "SELECT * FROM mobiuser where id = %s",
            (g.user['id'],)
        )
        res_user = curs.fetchone()
        academic = res_user['academic']

    # we need 2 dicts:
    # - one for data that will be presented to the world via the API: external_data
    # - a second one for data required for web pages presentation: internal_data
    external_data = {
        'variantId': None,
        'gene': {
            'symbol': None,
            'RefSeqTranscript': None,
            'nmVersion': None,
            'RefSeqNg': None,
            'RefSeqNp': None,
            'ENST': None,
            'ENSP': None,
            'canonical': None,
            'previousSymbols_aliases': None,
            'hgncId': None,
            'chromosome': None,
            'strand': None,
            'numberOfExons': None,
            'proteinName': None,
            'proteinShortName': None,
            'proteinSize': None,
            'uniprotId': None,
        },
        'nomenclatures': {
            'cName': None,
            'ngName': None,
            'ivsName': None,
            'pName': None,
            'hg19gName': None,
            'hg19StrictgName': None,
            'hg19PseudoVCF': None,
            'hg38gName': None,
            'hg38StrictgName': None,
            'hg38PseudoVCF': None,
        },
        'VCF': {
            'chr': None,
            'hg19': {
                'ncbiChr': None,
                'pos': None,
                'ref': None,
                'alt': None,
            },
            'hg38': {
                'ncbiChr': None,
                'pos': None,
                'ref': None,
                'alt': None,
            }
        },
        'sequences': {
            'wildType': None,
            'mutant': None,
        },
        'positions': {
            'DNAType': None,
            'RNAType': None,
            'proteinType': None,
            'proteinTypeSoAccession': None,
            'segmentStartType': None,
            'segmentStartNumber': None,
            'segmentEndType': None,
            'segmentEndNumber': None,
            'size': None,
            'nearestSsDist': None,
            'nearestSsType': None,
            'aaPositionStart': None,
            'aaPositionEnd': None,
            'proteinDomain': [],
            'metaDomednds': None,
            'metaDomeTolerance': None,
            'metaDomeTranscriptId': None,
        },
        'admin': {
            'creationDate': None,
            'creationUserName': None,
        },
        'frequenciesDatabases': {
            'gnomADv2Exome': None,
            'gnomADv2Genome': None,
            'gnomADv3': None,
            'dbSNPrsid': None,
            'clinvarId': None,
            'clinvarClinsigConf': None,
            'clinvarClinsig': None,
        },
        'overallPredictions': {
            'caddRaw': None,
            'caddPhred': None,
            'eigenRaw': None,
            'eigenPhred': None,
            'mpaScore': None,
            'mpaImpact': None,
        },
        'splicingPredictions': {
            'mes5': None,
            'mes3': None,
            'dbscSNVADA': None,
            'dbscSNVRF': None,
            'spliceai_DS_AG': None,
            'spliceai_DS_AL': None,
            'spliceai_DS_DG': None,
            'spliceai_DS_DL': None,
            'spliceai_DP_AG': None,
            'spliceai_DP_AL': None,
            'spliceai_DP_DG': None,
            'spliceai_DP_DL': None,
            'SPiP': None,
        },
        'miRNATargetSitesPredictions': {
            'mirandaCategory': None,
            'mirandaRankScore': None,
            'mirandaMaxDiff': None,
            'mirandaRefBestMir': None,
            'mirandaRefBestScore': None,
            'mirandaAltBestMir': None,
            'mirandaAltBestScore': None,
            'targetScanCategory': None,
            'targetScanRankScore': None,
            'targetScanMaxDiff': None,
            'targetScanRefBestMir': None,
            'targetScanRefBestScore': None,
            'targetScanAltBestMir': None,
            'targetScanAltBestScore': None,
            'RNAHybridCategory': None,
            'RNAHybridRankScore': None,
            'RNAHybridMaxDiff': None,
            'RNAHybridRefBestMir': None,
            'RNAHybridRefBestScore': None,
            'RNAHybridAltBestMir': None,
            'RNAHybridAltBestScore': None,
        },
        'missensePredictions': {
            'siftScore': None,
            'siftPred': None,
            'polyphen2HdivScore': None,
            'polyphen2HdivPred': None,
            'polyphen2HvarScore': None,
            'polyphen2HvarPred': None,
            'revelScore': None,
            'revelPred': None,
            'clinpredScore': None,
            'clinpredPred': None,
            'fathmmScore': None,
            'fathmmPred': None,
            'fathmmMklScore': None,
            'fathmmMklPred': None,
            'proveanScore': None,
            'proveanPred': None,
            'lrtScore': None,
            'lrtPred': None,
            'mutationTasterScore': None,
            'mutationTasterPred': None,
            'metaSVMScore': None,
            'metaSVMPred': None,
            'metaLRScore': None,
            'metaLRPred': None,
            'metaSVMLRRel': None,
            'misticScore': None,
            'misticPred': None,
        },
    }
    internal_data = {
        'admin': {
            'creationUser': None,
            'creationUserEmail': None,
        },
        'nomenclatures': {
            'cName': None,
            'ngName': None,
            'pName': None,
        },
        'VCF': {
            'hg19': {
                'gName': None,
            },
            'hg38': {
                'gName': None,
            }
        },
        'frequenciesDatabases': {
            'dbSNPrsid': None,
        },
        'hexosplice': {
            'exonSequence': None,
            'exonFirstNtCdnaPosition': None,
            'substitutionNature': None,
        },
        'canvas': {
            'segmentSize': None,
            'preceedingSegmentType': None,
            'preceedingSegmentNumber': None,
            'followingSegmentType': None,
            'followingSegmentNumber': None,
            'posIntronCanvas': None,
            'posExonCanvas': None,
        },
        'overallPredictions': {
            'mpaColor': None,
        },
        'splicingPredictions': {
            'splicingRadarLabels': [],
            'splicingRadarValues': [],
            'dbscSNVADAColor': None,
            'dbscSNVRFColor': None,
            'nat3ssScore': None,
            'nat3ssSeq': None,
            'nat5ssScore': None,
            'nat5ssSeq': None,
            'spliceai_DS_AG_color': None,
            'spliceai_DS_AL_color': None,
            'spliceai_DS_DG_color': None,
            'spliceai_DS_DL_color': None,
        },
        'positions': {
            'metaDomeColor': None,
            'distFromExon': None,
            'substitutionNature': None,
            'neighbourExonNumber': None,
            'insSize': None,
        },
        'missensePredictions': {
            'siftStar': None,
            'siftColor': None,
            'polyphen2HdivStar': None,
            'polyphen2HdivColor': None,
            'polyphen2HvarStar': None,
            'polyphen2HvarColor': None,
            'fathmmStar': None,
            'fathmmColor': None,
            'fathmmMklStar': None,
            'fathmmMklColor': None,
            'proveanStar': None,
            'lrtStar': None,
            'mutationTasterStar': None,
            'clinpredStar': None,
            'clinpredColor': None,
            'revelStar': None,
            'metaSVMColor': None,
            'metaLRColor': None,
            'misticColor': None,
        },
        'noMatch': {
            'cadd': None,
            'eigen': None,
            'dbnsfp': None,
            'dbmts': None,
            'spliceai': None,
        }
    }

    # get all variant_features and gene info
    curs.execute(
        "SELECT a.*, b.*, a.id as var_id, c.id as mobiuser_id, c.email, c.username,  d.so_accession \
        FROM variant_feature a, gene b, mobiuser c, valid_prot_type d \
        WHERE a.gene_name = b.name AND a.creation_user = c.id \
        AND a.prot_type = d.prot_type AND a.id = %s",
        (variant_id,)
    )
    variant_features = curs.fetchone()
    if variant_features:

        # length of c_name for printing on screen
        var_cname = variant_features['c_name']
        if len(var_cname) > 30:
            match_obj = re.search(r'(.+ins)[ATGC]+$', var_cname)
            if match_obj:
                var_cname = match_obj.group(1)

        # fill in dicts
        external_data['variantId'] = variant_features['var_id']
        external_data['nomenclatures']['cName'] = 'c.{}'.format(variant_features['c_name'])
        external_data['nomenclatures']['ngName'] = 'g.{}'.format(variant_features['ng_name'])
        external_data['nomenclatures']['ivsName'] = variant_features['ivs_name']
        external_data['nomenclatures']['pName'] = 'p.{}'.format(variant_features['p_name'])
        external_data['sequences']['wildType'] = variant_features['wt_seq']
        external_data['sequences']['mutant'] = variant_features['mt_seq']

        # for HTML webpages
        internal_data['nomenclatures']['cName'] = var_cname
        internal_data['nomenclatures']['ngName'] = variant_features['ng_name']
        internal_data['nomenclatures']['pName'] = variant_features['p_name']

        external_data['gene']['symbol'] = variant_features['gene_name'][0]
        external_data['gene']['RefSeqTranscript'] = variant_features['gene_name'][1]
        external_data['gene']['nmVersion'] = variant_features['nm_version']
        external_data['gene']['RefSeqNg'] = variant_features['ng']
        external_data['gene']['RefSeqNp'] = variant_features['np']
        external_data['gene']['ENST'] = variant_features['enst']
        external_data['gene']['ENSP'] = variant_features['ensp']
        external_data['gene']['canonical'] = variant_features['canonical']
        external_data['gene']['previousSymbols_aliases'] = variant_features['second_name']
        external_data['gene']['hgncId'] = variant_features['hgnc_id']
        external_data['gene']['chromosome'] = variant_features['chr']
        external_data['gene']['strand'] = variant_features['strand']
        external_data['gene']['numberOfExons'] = variant_features['number_of_exons']
        external_data['gene']['proteinName'] = variant_features['prot_name']
        external_data['gene']['proteinShortName'] = variant_features['prot_short']
        external_data['gene']['proteinSize'] = variant_features['prot_size']
        external_data['gene']['uniprotId'] = variant_features['uniprot_id']

        external_data['positions']['DNAType'] = variant_features['dna_type']
        external_data['positions']['RNAType'] = variant_features['rna_type']
        external_data['positions']['proteinType'] = variant_features['prot_type']
        external_data['positions']['proteinTypeSoAccession'] = variant_features['so_accession']
        external_data['positions']['segmentStartType'] = variant_features['start_segment_type']
        external_data['positions']['segmentStartNumber'] = variant_features['start_segment_number']
        external_data['positions']['segmentEndType'] = variant_features['end_segment_type']
        external_data['positions']['segmentEndNumber'] = variant_features['end_segment_number']
        external_data['positions']['size'] = variant_features['variant_size']

        external_data['admin']['creationDate'] = variant_features['creation_date']
        internal_data['admin']['creationUser'] = variant_features['mobiuser_id']
        internal_data['admin']['creationUserEmail'] = variant_features['email']
        external_data['admin']['creationUserName'] = variant_features['username']

        external_data['frequenciesDatabases']['dbSNPrsid'] = 'rs{}'.format(variant_features['dbsnp_id'])
        internal_data['frequenciesDatabases']['dbSNPrsid'] = variant_features['dbsnp_id']

        if variant_features['dna_type'] == 'indel':
            match_obj = re.search(r'ins([ATGC]+)$', variant_features['c_name'])
            if match_obj:
                internal_data['positions']['insSize'] = len(match_obj.group(1))
        # get variant info
        curs.execute(
            "SELECT * FROM variant WHERE feature_id = %s",
            (variant_id,)
        )
        variant = curs.fetchall()

        aa_pos = None
        # pos_splice_site = None
        domain = None
        # favourite var?
        curs.execute(
            "SELECT mobiuser_id FROM mobiuser_favourite WHERE feature_id = %s",
            (variant_id,)
        )
        favourite = curs.fetchone()
        if favourite is not None and \
                g.user is not None:
            if favourite['mobiuser_id'] == g.user['id']:
                favourite = True
        splicing_radar_labels = []
        splicing_radar_values = []
        for var in variant:
            if var['genome_version'] == 'hg38':
                # HGVS strict genomic names e.g. NC_000001.11:g.216422237G>A
                curs.execute(
                    "SELECT ncbi_name \
                    FROM chromosomes WHERE name = %s and genome_version = %s",
                    (var['chr'], var['genome_version'])
                )
                res_chr = curs.fetchone()
                external_data['VCF']['chr'] = var['chr']
                external_data['VCF']['hg38']['ncbiChr'] = res_chr['ncbi_name']
                external_data['VCF']['hg38']['pos'] = var['pos']
                external_data['VCF']['hg38']['ref'] = var['pos_ref']
                external_data['VCF']['hg38']['alt'] = var['pos_alt']
                internal_data['VCF']['hg38']['gName'] = var['g_name']
                external_data['nomenclatures']['hg38PseudoVCF'] = '{0}-{1}-{2}-{3}'.format(
                    var['chr'], var['pos'], var['pos_ref'], var['pos_alt']
                )
                external_data['nomenclatures']['hg38StrictgName'] = '{0}:g.{1}'.format(
                    res_chr['ncbi_name'], var['g_name']
                )
                external_data['nomenclatures']['hg38gName'] = 'chr{0}:g.{1}'.format(var['chr'], var['g_name'])

                # compute position / splice sites
                if variant_features['variant_size'] < 50 and \
                        variant_features['start_segment_type'] == 'exon':
                    curs.execute(
                        "SELECT * FROM segment WHERE genome_version = %s\
                        AND gene_name[1] = %s and gene_name[2] = %s \
                        AND type = 'exon' AND number = %s",
                        (var['genome_version'],
                            variant_features['gene_name'][0],
                            variant_features['gene_name'][1],
                            variant_features['start_segment_number'])
                    )
                    positions = curs.fetchone()
                    # get info to build hexoSplice link
                    if variant_features['dna_type'] == 'substitution':
                        internal_data['hexosplice']['exonSequence'] = md_utilities.get_exon_sequence(
                            positions, var['chr'], variant_features['strand']
                        )
                        internal_data['hexosplice']['exonFirstNtCdnaPosition'] = md_utilities.get_exon_first_nt_cdna_position(
                            positions, var['pos'], variant_features['c_name']
                        )
                        if internal_data['hexosplice']['exonFirstNtCdnaPosition'] < 1:
                            internal_data['hexosplice']['substitutionNature'] = md_utilities.get_substitution_nature(
                                variant_features['c_name']
                            )
                    # get a tuple ['site_type', 'dist(bp)']
                    (external_data['positions']['nearestSsType'],
                        external_data['positions']['nearestSsDist']) = md_utilities.get_pos_splice_site(var['pos'], positions)
                    # relative position in exon for canvas drawing
                    # get a tuple ['relative position in exon canvas', 'segment_size']
                    (internal_data['canvas']['posExonCanvas'], internal_data['canvas']['segmentSize']) = md_utilities.get_pos_exon_canvas(
                        var['pos'], positions
                    )
                    # get neighbours type, number
                    (internal_data['canvas']['preceedingSegmentType'], internal_data['canvas']['preceedingSegmentNumber'],
                        internal_data['canvas']['followingSegmentType'], internal_data['canvas']['followingSegmentNumber']) = md_utilities.get_exon_neighbours(db, positions)
                    # get natural ss maxent scores
                    if internal_data['canvas']['preceedingSegmentNumber'] != 'UTR':
                        (internal_data['splicingPredictions']['nat3ssScore'], internal_data['splicingPredictions']['nat3ssSeq']) = md_utilities.get_maxent_natural_sites_scores(
                            var['chr'], variant_features['strand'], 3, positions
                        )
                    if internal_data['canvas']['followingSegmentNumber'] != 'UTR':
                        (internal_data['splicingPredictions']['nat5ssScore'], internal_data['splicingPredictions']['nat5ssSeq']) = md_utilities.get_maxent_natural_sites_scores(
                            var['chr'], variant_features['strand'], 5, positions
                        )
                    # compute position in domain
                    # 1st get aa pos
                    if variant_features['prot_type'] != 'unknown':
                        aa_pos = md_utilities.get_aa_position(variant_features['p_name'])
                        external_data['positions']['aaPositionStart'] = aa_pos[0]
                        external_data['positions']['aaPositionEnd'] = aa_pos[1]
                        curs.execute(
                            "SELECT * FROM protein_domain WHERE gene_name[2] = '{0}' AND (('{1}' \
                            BETWEEN aa_start AND aa_end) OR ('{2}' BETWEEN aa_start AND aa_end));".format(
                                variant_features['gene_name'][1], aa_pos[0], aa_pos[1]
                            )
                        )
                        domains = curs.fetchall()
                        for domain in domains:
                            external_data['positions']['proteinDomain'].append([domain['name'], domain['aa_start'], domain['aa_end']])

                        # metadome data?
                        if variant_features['dna_type'] == 'substitution' and \
                                os.path.isfile('{0}{1}.json'.format(md_utilities.local_files['metadome']['abs_path'], variant_features['enst'])) is True:
                            # get value in json file
                            with open('{0}{1}.json'.format(md_utilities.local_files['metadome']['abs_path'], variant_features['enst']), "r") as metad_file:
                                metad_json = json.load(metad_file)
                                if 'positional_annotation' in metad_json:
                                    for pos in metad_json['positional_annotation']:
                                        if int(pos['protein_pos']) == int(aa_pos[0]):
                                            if 'sw_dn_ds' in pos:
                                                external_data['positions']['metaDomednds'] = "{:.2f}".format(float(pos['sw_dn_ds']))
                                                [external_data['positions']['metaDomeTolerance'], internal_data['positions']['metaDomeColor']] = md_utilities.get_metadome_colors(external_data['positions']['metaDomednds'])
                                if 'transcript_id' in metad_json:
                                    external_data['positions']['metadomeTranscript'] = metad_json['transcript_id']
                if variant_features['start_segment_type'] == 'intron':
                    internal_data['positions']['distFromExon'], sign = md_utilities.get_pos_splice_site_intron(variant_features['c_name'])
                    if variant_features['dna_type'] == 'substitution':
                        internal_data['positions']['substitutionNature'] = md_utilities.get_substitution_nature(variant_features['c_name'])
                # MPA indel splice
                elif variant_features['start_segment_type'] == 'intron' and \
                        (variant_features['dna_type'] == 'indel' or
                            variant_features['dna_type'] == 'deletion' or
                            variant_features['dna_type'] == 'duplication') and \
                        variant_features['variant_size'] < 50:
                    if internal_data['positions']['distFromExon'] <= 20 and \
                            (not external_data['overallPredictions']['mpaScore'] or external_data['overallPredictions']['mpaScore'] < 6):
                        external_data['overallPredictions']['mpaScore'] = 6
                        external_data['overallPredictions']['mpaImpact'] = 'Splice indel'
                # intronic variant canvas
                if variant_features['start_segment_type'] == 'intron' and \
                        internal_data['positions']['distFromExon'] <= 100 and \
                        variant_features['variant_size'] < 50:
                    internal_data['canvas']['posIntronCanvas'] = 200 - internal_data['positions']['distFromExon']  # relative position inside canvas fomr exon beginning
                    internal_data['positions']['neighbourExonNumber'] = variant_features['start_segment_number'] + 1
                    if sign == '+':
                        internal_data['positions']['neighbourExonNumber'] = variant_features['start_segment_number']
                        internal_data['canvas']['posIntronCanvas'] = 400 + internal_data['positions']['distFromExon']  # relative position inside canvas from exon end

                    internal_data['canvas']['posExonCanvas'] = None
                    # get info from neighboring exon
                    curs.execute(
                        "SELECT * FROM segment WHERE genome_version = %s\
                        AND gene_name[1] = %s and gene_name[2] = %s AND type = 'exon' AND number = %s",
                        (var['genome_version'], variant_features['gene_name'][0], variant_features['gene_name'][1], internal_data['positions']['neighbourExonNumber'])
                    )
                    positions_neighb_exon = curs.fetchone()
                    if sign == '+':
                        internal_data['canvas']['preceedingSegmentType'] = None
                        internal_data['canvas']['preceedingSegmentNumber'] = None
                        internal_data['canvas']['followingSegmentType'] = 'intron'
                        internal_data['canvas']['followingSegmentNumber'] = variant_features['start_segment_number']
                        (internal_data['splicingPredictions']['nat5ssScore'], internal_data['splicingPredictions']['nat5ssSeq']) = md_utilities.get_maxent_natural_sites_scores(
                            var['chr'], variant_features['strand'], 5, positions_neighb_exon
                        )
                    else:
                        internal_data['canvas']['preceedingSegmentType'] = 'intron'
                        internal_data['canvas']['preceedingSegmentNumber'] = variant_features['start_segment_number']
                        internal_data['canvas']['followingSegmentType'] = None
                        internal_data['canvas']['followingSegmentNumber'] = None
                        (internal_data['splicingPredictions']['nat3ssScore'], internal_data['splicingPredictions']['nat3ssSeq']) = md_utilities.get_maxent_natural_sites_scores(
                            var['chr'], variant_features['strand'], 3, positions_neighb_exon
                        )
                # clinvar
                record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38']['abs_path'], var, variant_features)
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['clinvarClinsig'] = "{0} {1}".format(record, md_utilities.external_tools['ClinVar']['version'])
                else:
                    external_data['frequenciesDatabases']['clinvarId'] = record[2]
                    match_object = re.search(r'CLNSIG=(.+);CLNVC=', record[7])
                    if match_object:
                        match2_object = re.search(r'^(.+);CLNSIGCONF=(.+)$', match_object.group(1))
                        if match2_object:
                            external_data['frequenciesDatabases']['clinvarClinsig'] = match2_object.group(1)
                            external_data['frequenciesDatabases']['clinvarClinsigConf'] = match2_object.group(2)
                            external_data['frequenciesDatabases']['clinvarClinsigConf'] = external_data['frequenciesDatabases']['clinvarClinsigConf'].replace('%3B', '-')
                        else:
                            external_data['frequenciesDatabases']['clinvarClinsig'] = match_object.group(1)
                    elif re.search(r'CLNREVSTAT=no_interpretation_for_the_single_variant', record[7]):
                        external_data['frequenciesDatabases']['clinvarClinsig'] = 'No interpretation for the single variant'
                    if external_data['frequenciesDatabases']['clinvarClinsig'] and \
                            re.search('pathogenic', external_data['frequenciesDatabases']['clinvarClinsig'], re.IGNORECASE) and \
                            not re.search('pathogenicity', external_data['frequenciesDatabases']['clinvarClinsig'], re.IGNORECASE):
                        external_data['overallPredictions']['mpaScore'] = 10
                        external_data['overallPredictions']['mpaImpact'] = 'Clinvar pathogenic'
                # MPA PTC
                if not external_data['overallPredictions']['mpaScore'] or \
                        external_data['overallPredictions']['mpaImpact'] != 'Clinvar pathogenic':
                    if variant_features['prot_type'] == 'nonsense' or \
                            variant_features['prot_type'] == 'frameshift':
                        external_data['overallPredictions']['mpaScore'] = 10
                        external_data['overallPredictions']['mpaImpact'] = variant_features['prot_type']
                # gnomadv3
                record = md_utilities.get_value_from_tabix_file('gnomADv3', md_utilities.local_files['gnomad_3']['abs_path'], var, variant_features)
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['gnomADv3'] = record
                else:
                    # print(record)
                    external_data['frequenciesDatabases']['gnomADv3'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                # dbNSFP
                if variant_features['prot_type'] == 'missense':
                    # CADD
                    record = md_utilities.get_value_from_tabix_file('dbnsfp', md_utilities.local_files['dbnsfp']['abs_path'], var, variant_features)
                    # print(record)
                    if academic is True:
                        try:
                            external_data['overallPredictions']['caddRaw'] = format(float(record[int(md_utilities.external_tools['CADD']['dbNSFP_value_col'])]), '.2f')
                            external_data['overallPredictions']['caddPhred'] = format(float(record[int(md_utilities.external_tools['CADD']['dbNSFP_phred_col'])]), '.2f')
                        except Exception:
                            internal_data['noMatch']['cadd'] = 'No match in dbNSFP for CADD'
                        if 'caddRaw' in external_data['overallPredictions'] and \
                                external_data['overallPredictions']['caddRaw'] == '.':
                            internal_data['noMatch']['cadd'] = 'No score in dbNSFP for CADD'
                    # Eigen
                    try:
                        external_data['overallPredictions']['eigenRaw'] = format(float(record[int(md_utilities.external_tools['Eigen']['dbNSFP_value_col'])]), '.2f')
                        external_data['overallPredictions']['eigenPhred'] = format(float(record[int(md_utilities.external_tools['Eigen']['dbNSFP_pred_col'])]), '.2f')
                    except Exception:
                        internal_data['noMatch']['eigen'] = 'No match in dbNSFP for Eigen'
                    if 'eigenRaw' in external_data['overallPredictions'] and \
                            external_data['overallPredictions']['eigenRaw'] == '.':
                        internal_data['noMatch']['eigen'] = 'No score in dbNSFP for Eigen'
                    # record comes from CADD section above
                    if isinstance(record, str):
                        internal_data['noMatch']['dbnsfp'] = "{0} {1}".format(record, md_utilities.external_tools['dbNSFP']['version'])
                    else:
                        # first: get enst we're dealing with
                        i = 0
                        transcript_index = 0
                        enst_list = re.split(';', record[14])
                        if len(enst_list) > 1:
                            for enst in enst_list:
                                if variant_features['enst'] == enst:
                                    transcript_index = i
                                i += 1
                        # print(transcript_index)
                        # then iterate for each score of interest, e.g.  sift..
                        # missense:
                        # mpa score
                        mpa_missense = 0
                        mpa_avail = 0
                        # sift
                        external_data['missensePredictions']['siftScore'], external_data['missensePredictions']['siftPred'], internal_data['missensePredictions']['siftStar'] = md_utilities.getdbNSFP_results(
                            transcript_index, int(md_utilities.external_tools['SIFT']['dbNSFP_value_col']), int(md_utilities.external_tools['SIFT']['dbNSFP_pred_col']), ';', 'basic', 1.1, 'lt', record
                        )

                        internal_data['missensePredictions']['siftColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['siftScore'], 'sift')
                        if external_data['missensePredictions']['siftPred'] == 'Damaging':
                            mpa_missense += 1
                        if external_data['missensePredictions']['siftPred'] != 'no prediction':
                            mpa_avail += 1
                        if academic is True:
                            # polyphen 2 hdiv
                            external_data['missensePredictions']['polyphen2HdivScore'], external_data['missensePredictions']['polyphen2HdivPred'], internal_data['missensePredictions']['polyphen2HdivStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.external_tools['Polyphen-2']['dbNSFP_value_col_hdiv']), int(md_utilities.external_tools['Polyphen-2']['dbNSFP_pred_col_hdiv']), ';', 'pph2', -0.1, 'gt', record
                            )

                            internal_data['missensePredictions']['polyphen2HdivColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['polyphen2HdivScore'], 'pph2_hdiv_mid', 'pph2_hdiv_max')
                            if re.search('Damaging', external_data['missensePredictions']['polyphen2HdivPred']):
                                mpa_missense += 1
                            if external_data['missensePredictions']['polyphen2HdivPred'] != 'no prediction':
                                mpa_avail += 1
                            # hvar
                            external_data['missensePredictions']['polyphen2HvarScore'], external_data['missensePredictions']['polyphen2HvarPred'], internal_data['missensePredictions']['polyphen2HvarStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.external_tools['Polyphen-2']['dbNSFP_value_col_hvar']), int(md_utilities.external_tools['Polyphen-2']['dbNSFP_pred_col_hvar']), ';', 'pph2', -0.1, 'gt', record
                            )

                            internal_data['missensePredictions']['polyphen2HvarColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['polyphen2HvarScore'], 'pph2_hvar_mid', 'pph2_hvar_max')
                            if re.search('Damaging', external_data['missensePredictions']['polyphen2HvarPred']):
                                mpa_missense += 1
                            if external_data['missensePredictions']['polyphen2HvarPred'] != 'no prediction':
                                mpa_avail += 1
                        # fathmm
                        external_data['missensePredictions']['fathmmScore'], external_data['missensePredictions']['fathmmPred'], internal_data['missensePredictions']['fathmmStar'] = md_utilities.getdbNSFP_results(
                            transcript_index, int(md_utilities.external_tools['FatHMM']['dbNSFP_value_col']), int(md_utilities.external_tools['FatHMM']['dbNSFP_pred_col']), ';', 'basic', 20, 'lt', record
                        )

                        internal_data['missensePredictions']['fathmmColor'] = md_utilities.get_preditor_single_threshold_reverted_color(external_data['missensePredictions']['fathmmScore'], 'fathmm')
                        if external_data['missensePredictions']['fathmmPred'] == 'Damaging':
                            mpa_missense += 1
                        if external_data['missensePredictions']['fathmmPred'] != 'no prediction':
                            mpa_avail += 1
                        # fathmm-mkl -- not displayed
                        external_data['missensePredictions']['fathmmMklScore'], external_data['missensePredictions']['fathmmMklPred'], internal_data['missensePredictions']['fathmmMklStar'] = md_utilities.getdbNSFP_results(
                            transcript_index, int(md_utilities.hidden_external_tools['FatHMM-MKL']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['FatHMM-MKL']['dbNSFP_pred_col']), ';', 'basic', 20, 'lt', record
                        )

                        internal_data['missensePredictions']['fathmmMklColor'] = md_utilities.get_preditor_single_threshold_reverted_color(external_data['missensePredictions']['fathmmMklScore'], 'fathmm-mkl')
                        if external_data['missensePredictions']['fathmmMklPred'] == 'Damaging':
                            mpa_missense += 1
                        if external_data['missensePredictions']['fathmmMklPred'] != 'no prediction':
                            mpa_avail += 1
                        # provean -- not displayed
                        external_data['missensePredictions']['proveanScore'], external_data['missensePredictions']['proveanPred'], internal_data['missensePredictions']['proveanStar'] = md_utilities.getdbNSFP_results(
                            transcript_index, int(md_utilities.hidden_external_tools['Provean']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['Provean']['dbNSFP_pred_col']), ';', 'basic', 20, 'lt', record
                        )
                        if external_data['missensePredictions']['proveanPred'] == 'Damaging':
                            mpa_missense += 1
                        if external_data['missensePredictions']['proveanPred'] != 'no prediction':
                            mpa_avail += 1
                        # LRT -- not displayed
                        external_data['missensePredictions']['lrtScore'], external_data['missensePredictions']['lrtPred'], internal_data['missensePredictions']['lrtStar'] = md_utilities.getdbNSFP_results(
                            transcript_index, int(md_utilities.hidden_external_tools['LRT']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['LRT']['dbNSFP_pred_col']), ';', 'basic', -1, 'gt', record
                        )

                        if external_data['missensePredictions']['lrtPred'] == 'Damaging':
                            mpa_missense += 1
                        if re.search(r'^[DUN]', external_data['missensePredictions']['lrtPred']):
                            mpa_avail += 1
                        # MutationTaster -- not displayed
                        external_data['missensePredictions']['mutationTasterScore'], external_data['missensePredictions']['mutationTasterPred'], internal_data['missensePredictions']['mutationTasterStar'] = md_utilities.getdbNSFP_results(
                            transcript_index, int(md_utilities.hidden_external_tools['MutationTaster']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['MutationTaster']['dbNSFP_pred_col']), ';', 'mt', -1, 'gt', record
                        )

                        if re.search('Disease causing', external_data['missensePredictions']['mutationTasterPred']):
                            mpa_missense += 1
                        if external_data['missensePredictions']['mutationTasterPred'] != 'no prediction':
                            mpa_avail += 1
                        if academic is True:
                            # ClinPred
                            external_data['missensePredictions']['clinpredScore'], external_data['missensePredictions']['clinpredPred'], internal_data['missensePredictions']['clinpredStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.external_tools['ClinPred']['dbNSFP_value_col']), int(md_utilities.external_tools['ClinPred']['dbNSFP_pred_col']), ';', 'basic', '-1', 'gt', record
                            )
                            # clinpred score in dbNSFP, contrary to other scores, presents with 9-10 numbers after '.'
                            try:
                                external_data['missensePredictions']['clinpredScore'] = format(float(external_data['missensePredictions']['clinpredScore']), '.3f')
                                internal_data['missensePredictions']['clinpredColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['clinpredScore'], 'clinpred')
                            except Exception:
                                pass

                        # REVEL
                            external_data['missensePredictions']['revelScore'], external_data['missensePredictions']['revelPred'], internal_data['missensePredictions']['revelStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.external_tools['REVEL']['dbNSFP_value_col']), int(md_utilities.external_tools['REVEL']['dbNSFP_pred_col']), ';', 'basic', '-1', 'gt', record
                            )

                            # no REVEL pred in dbNSFP => custom
                            if external_data['missensePredictions']['revelScore'] != '.' and \
                                    float(external_data['missensePredictions']['revelScore']) < 0.2:
                                external_data['missensePredictions']['revelPred'] = md_utilities.predictors_translations['revel']['B']
                            elif external_data['missensePredictions']['revelScore'] != '.' and \
                                    float(external_data['missensePredictions']['revelScore']) > 0.5:
                                external_data['missensePredictions']['revelPred'] = md_utilities.predictors_translations['revel']['D']
                            elif external_data['missensePredictions']['revelScore'] != '.':
                                external_data['missensePredictions']['revelPred'] = md_utilities.predictors_translations['revel']['U']
                            else:
                                external_data['missensePredictions']['revelPred'] = 'no prediction'

                            internal_data['missensePredictions']['revelColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['revelScore'], 'revel_min', 'revel_max')

                        # meta SVM
                        external_data['missensePredictions']['metaSVMScore'] = record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_msvm'])]
                        internal_data['missensePredictions']['metaSVMColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['metaSVMScore'], 'meta-svm')
                        external_data['missensePredictions']['metaSVMPred'] = md_utilities.predictors_translations['basic'][record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_pred_msvm'])]]
                        if external_data['missensePredictions']['metaSVMPred'] == 'Damaging':
                            mpa_missense += 1
                        if external_data['missensePredictions']['metaSVMPred'] != 'no prediction':
                            mpa_avail += 1
                        # meta LR
                        external_data['missensePredictions']['metaLRScore'] = record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_mlr'])]
                        internal_data['missensePredictions']['metaLRColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['metaLRScore'], 'meta-lr')
                        external_data['missensePredictions']['metaLRPred'] = md_utilities.predictors_translations['basic'][record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_pred_mlr'])]]
                        if external_data['missensePredictions']['metaLRPred'] == 'Damaging':
                            mpa_missense += 1
                        if external_data['missensePredictions']['metaLRPred'] != 'no prediction':
                            mpa_avail += 1
                        external_data['missensePredictions']['metaSVMLRRel'] = record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_mrel'])]  # reliability index for meta score (1-10): the higher, the higher the reliability
                        if ((not external_data['overallPredictions']['mpaScore'] or
                                external_data['overallPredictions']['mpaScore'] < mpa_missense) and
                                mpa_avail > 0):
                            external_data['overallPredictions']['mpaScore'] = float('{0:.2f}'.format((mpa_missense / mpa_avail) * 10))
                            if external_data['overallPredictions']['mpaScore'] >= 8:
                                external_data['overallPredictions']['mpaImpact'] = 'High missense'
                            elif external_data['overallPredictions']['mpaScore'] >= 6:
                                external_data['overallPredictions']['mpaImpact'] = 'Moderate missense'
                            else:
                                external_data['overallPredictions']['mpaImpact'] = 'Low missense'
                # dbMTS
                if variant_features['dna_type'] == 'substitution' and \
                        re.search(r'^\*', variant_features['c_name']):
                    record = md_utilities.get_value_from_tabix_file('dbmts', md_utilities.local_files['dbmts']['abs_path'], var, variant_features)
                    if isinstance(record, str):
                        internal_data['noMatch']['dbmts'] = "{0} {1}".format(record, md_utilities.external_tools['dbMTS']['version'])
                    else:
                        # Eigen from dbMTS for 3'UTR variants
                        try:
                            external_data['overallPredictions']['eigenRaw'] = format(float(record[int(md_utilities.external_tools['Eigen']['dbMTS_value_col'])]), '.2f')
                            external_data['overallPredictions']['eigenPhred'] = format(float(record[int(md_utilities.external_tools['Eigen']['dbMTS_pred_col'])]), '.2f')
                        except Exception:
                            external_data['overallPredictions']['eigen'] = 'No match in dbMTS for Eigen'
                        if 'eigen_raw' in external_data['overallPredictions'] and \
                                external_data['overallPredictions']['eigenRaw'] == '.':
                            external_data['overallPredictions']['eigen'] = 'No score in dbMTS for Eigen'
                        try:
                            # Miranda
                            external_data['miRNATargetSitesPredictions']['mirandaCategory'] = record[int(md_utilities.external_tools['dbMTS']['miranda_cat_col'])]
                            external_data['miRNATargetSitesPredictions']['mirandaRankScore'] = record[int(md_utilities.external_tools['dbMTS']['miranda_rankscore_col'])]
                            external_data['miRNATargetSitesPredictions']['mirandaMaxDiff'] = record[int(md_utilities.external_tools['dbMTS']['miranda_maxdiff_col'])]
                            external_data['miRNATargetSitesPredictions']['mirandaRefBestMir'] = md_utilities.format_mirs(record[int(md_utilities.external_tools['dbMTS']['miranda_refbestmir_col'])])
                            external_data['miRNATargetSitesPredictions']['mirandaRefBestScore'] = record[int(md_utilities.external_tools['dbMTS']['miranda_refbestscore_col'])]
                            external_data['miRNATargetSitesPredictions']['mirandaAltBestMir'] = md_utilities.format_mirs(record[int(md_utilities.external_tools['dbMTS']['miranda_altbestmir_col'])])
                            external_data['miRNATargetSitesPredictions']['mirandaAltBestScore'] = record[int(md_utilities.external_tools['dbMTS']['miranda_altbestscore_col'])]
                            # TargetScan
                            external_data['miRNATargetSitesPredictions']['targetScanCategory'] = record[int(md_utilities.external_tools['dbMTS']['targetscan_cat_col'])]
                            external_data['miRNATargetSitesPredictions']['targetScanRankScore'] = record[int(md_utilities.external_tools['dbMTS']['targetscan_rankscore_col'])]
                            external_data['miRNATargetSitesPredictions']['targetScanMaxDiff'] = record[int(md_utilities.external_tools['dbMTS']['targetscan_maxdiff_col'])]
                            external_data['miRNATargetSitesPredictions']['targetScanRefBestMir'] = md_utilities.format_mirs(record[int(md_utilities.external_tools['dbMTS']['targetscan_refbestmir_col'])])
                            external_data['miRNATargetSitesPredictions']['targetScanRefBestScore'] = record[int(md_utilities.external_tools['dbMTS']['targetscan_refbestscore_col'])]
                            external_data['miRNATargetSitesPredictions']['targetScanAltBestMir'] = md_utilities.format_mirs(record[int(md_utilities.external_tools['dbMTS']['targetscan_altbestmir_col'])])
                            external_data['miRNATargetSitesPredictions']['targetScanAltBestScore'] = record[int(md_utilities.external_tools['dbMTS']['targetscan_altbestscore_col'])]
                            # RNAHybrid
                            external_data['miRNATargetSitesPredictions']['RNAHybridCategory'] = record[int(md_utilities.external_tools['dbMTS']['rnahybrid_cat_col'])]
                            external_data['miRNATargetSitesPredictions']['RNAHybridRankScore'] = record[int(md_utilities.external_tools['dbMTS']['rnahybrid_rankscore_col'])]
                            external_data['miRNATargetSitesPredictions']['RNAHybridMaxDiff'] = record[int(md_utilities.external_tools['dbMTS']['rnahybrid_maxdiff_col'])]
                            external_data['miRNATargetSitesPredictions']['RNAHybridRefBestMir'] = md_utilities.format_mirs(record[int(md_utilities.external_tools['dbMTS']['rnahybrid_refbestmir_col'])])
                            external_data['miRNATargetSitesPredictions']['RNAHybridRefBestScore'] = record[int(md_utilities.external_tools['dbMTS']['rnahybrid_refbestscore_col'])]
                            external_data['miRNATargetSitesPredictions']['RNAHybridAltBestMir'] = md_utilities.format_mirs(record[int(md_utilities.external_tools['dbMTS']['rnahybrid_altbestmir_col'])])
                            external_data['miRNATargetSitesPredictions']['RNAHybridAltBestScore'] = record[int(md_utilities.external_tools['dbMTS']['rnahybrid_altbestscore_col'])]
                        except Exception:
                            internal_data['noMatch']['dbmts'] = "{0} {1}".format(record, md_utilities.external_tools['dbMTS']['version'])

                # CADD
                if academic is True:
                    if variant_features['dna_type'] == 'substitution':
                        if variant_features['prot_type'] != 'missense':
                            # specific file for CADD
                            record = md_utilities.get_value_from_tabix_file('CADD', md_utilities.local_files['cadd']['abs_path'], var, variant_features)
                            if isinstance(record, str):
                                internal_data['noMatch']['cadd'] = "{0} {1}".format(record, md_utilities.external_tools['CADD']['version'])
                            else:
                                external_data['overallPredictions']['caddRaw'] = format(float(record[int(md_utilities.external_tools['CADD']['raw_col'])]), '.2f')
                                external_data['overallPredictions']['caddPhred'] = format(float(record[int(md_utilities.external_tools['CADD']['phred_col'])]), '.2f')
                    else:
                        record = md_utilities.get_value_from_tabix_file('CADD', md_utilities.local_files['cadd_indels']['abs_path'], var, variant_features)
                        if isinstance(record, str):
                            internal_data['noMatch']['cadd'] = "{0} {1}".format(record, md_utilities.external_tools['CADD']['version'])
                        else:
                            external_data['overallPredictions']['caddRaw'] = record[int(md_utilities.external_tools['CADD']['raw_col'])]
                            external_data['overallPredictions']['caddPhred'] = record[int(md_utilities.external_tools['CADD']['phred_col'])]
                # spliceAI 1.3
                # ##INFO=<ID=SpliceAI,Number=.,Type=String,Description="SpliceAIv1.3 variant annotation.
                # These include delta scores (DS) and delta positions (DP) for acceptor gain (AG), acceptor loss (AL), donor gain (DG), and donor loss (DL).
                # Format: ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL">
                spliceai_res = False
                if variant_features['dna_type'] == 'substitution':
                    record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai_snvs']['abs_path'], var, variant_features)
                    spliceai_res = True
                elif ((variant_features['dna_type'] == 'insertion' or
                        variant_features['dna_type'] == 'duplication') and
                        variant_features['variant_size'] == 1) or \
                        (variant_features['dna_type'] == 'deletion' and
                            variant_features['variant_size'] <= 4):
                    record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai_indels']['abs_path'], var, variant_features)
                    # print(record)
                    spliceai_res = True
                if spliceai_res is True:
                    if isinstance(record, str):
                        internal_data['noMatch']['spliceai'] = "{0} {1}".format(record, md_utilities.external_tools['spliceAI']['version'])
                    else:
                        spliceais = re.split(r'\|', record[7])
                        # ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL
                        splicing_radar_labels.extend(['SpliceAI Acc Gain', 'SpliceAI Acc Loss', 'SpliceAI Donor Gain', 'SpliceAI Donor Loss'])
                        order_list = ['DS_AG', 'DS_AL', 'DS_DG', 'DS_DL', 'DP_AG', 'DP_AL', 'DP_DG', 'DP_DL']
                        i = 2
                        for tag in order_list:
                            identifier = "spliceai_{}".format(tag)
                            external_data['splicingPredictions'][identifier] = spliceais[i]
                            if re.search(r'DS_', tag):
                                splicing_radar_values.append(spliceais[i])
                            i += 1
                            if re.match('spliceai_DS_', identifier):
                                id_color = "{}_color".format(identifier)
                                internal_data['splicingPredictions'][id_color] = md_utilities.get_spliceai_color(float(external_data['splicingPredictions'][identifier]))
                                if not external_data['overallPredictions']['mpaScore'] or \
                                        external_data['overallPredictions']['mpaScore'] < 10:
                                    if float(external_data['splicingPredictions'][identifier]) > md_utilities.predictor_thresholds['spliceai_max']:
                                        external_data['overallPredictions']['mpaScore'] = 10
                                        external_data['overallPredictions']['mpaImpact'] = 'High splice'
                                    elif float(external_data['splicingPredictions'][identifier]) > md_utilities.predictor_thresholds['spliceai_mid']:
                                        external_data['overallPredictions']['mpaScore'] = 8
                                        external_data['overallPredictions']['mpaImpact'] = 'Moderate splice'
                                    elif float(external_data['splicingPredictions'][identifier]) > md_utilities.predictor_thresholds['spliceai_min']:
                                        external_data['overallPredictions']['mpaScore'] = 6
                                        external_data['overallPredictions']['mpaImpact'] = 'Low splice'

            elif var['genome_version'] == 'hg19':
                # ncbi chr
                curs.execute(
                    "SELECT ncbi_name \
                    FROM chromosomes WHERE name = %s and genome_version = %s",
                    (var['chr'], var['genome_version'])
                )
                res_chr = curs.fetchone()
                external_data['VCF']['hg19']['ncbiChr'] = res_chr['ncbi_name']
                external_data['VCF']['hg19']['pos'] = var['pos']
                external_data['VCF']['hg19']['ref'] = var['pos_ref']
                external_data['VCF']['hg19']['alt'] = var['pos_alt']
                internal_data['VCF']['hg19']['gName'] = var['g_name']
                external_data['nomenclatures']['hg19PseudoVCF'] = '{0}-{1}-{2}-{3}'.format(var['chr'], var['pos'], var['pos_ref'], var['pos_alt'])
                external_data['nomenclatures']['hg19StrictgName'] = '{0}:g.{1}'.format(res_chr['ncbi_name'], var['g_name'])
                external_data['nomenclatures']['hg19gName'] = 'chr{0}:g.{1}'.format(var['chr'], var['g_name'])

                # gnomad ex
                record = md_utilities.get_value_from_tabix_file('gnomAD exome', md_utilities.local_files['gnomad_exome']['abs_path'], var, variant_features)
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['gnomADv2Exome'] = record
                else:
                    external_data['frequenciesDatabases']['gnomADv2Exome'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                # gnomad ge
                record = md_utilities.get_value_from_tabix_file('gnomAD genome', md_utilities.local_files['gnomad_genome']['abs_path'], var, variant_features)
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['gnomADv2Genome'] = record
                else:
                    external_data['frequenciesDatabases']['gnomADv2Genome'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                # clinpred
                if variant_features['prot_type'] == 'missense':
                    # mistic
                    record = md_utilities.get_value_from_tabix_file('Mistic', md_utilities.local_files['mistic']['abs_path'], var, variant_features)
                    if isinstance(record, str):
                        external_data['missensePredictions']['misticScore'] = record
                    else:
                        external_data['missensePredictions']['misticScore'] = record[4]
                    internal_data['missensePredictions']['misticColor'] = "#000000"
                    external_data['missensePredictions']['misticPred'] = 'no prediction'
                    if re.search(r'^[\d\.]+$', external_data['missensePredictions']['misticScore']):
                        external_data['missensePredictions']['misticScore'] = format(float(external_data['missensePredictions']['misticScore']), '.2f')
                        internal_data['missensePredictions']['misticColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['misticScore'], 'mistic')
                        external_data['missensePredictions']['misticPred'] = 'Tolerated'
                        if float(external_data['missensePredictions']['misticScore']) > md_utilities.predictor_thresholds['mistic']:
                            external_data['missensePredictions']['misticPred'] = 'Damaging'
                if variant_features['dna_type'] == 'substitution':
                    # dbscSNV
                    record = md_utilities.get_value_from_tabix_file('dbscSNV', md_utilities.local_files['dbscsnv']['abs_path'], var, variant_features)
                    if isinstance(record, str):
                        external_data['splicingPredictions']['dbscSNVADA'] = "{0} {1}".format(record, md_utilities.external_tools['dbscSNV']['version'])
                        external_data['splicingPredictions']['dbscSNVRF'] = "{0} {1}".format(record, md_utilities.external_tools['dbscSNV']['version'])
                        if external_data['splicingPredictions']['dbscSNVADA'] != 'No match in dbscSNV v1.1':
                            splicing_radar_labels.append('dbscSNV ADA')
                            splicing_radar_values.append(external_data['splicingPredictions']['dbscSNVADA'])
                        if external_data['splicingPredictions']['dbscSNVRF'] != 'No match in dbscSNV v1.1':
                            splicing_radar_labels.append('dbscSNV RF')
                            splicing_radar_values.append(external_data['splicingPredictions']['dbscSNVRF'])
                    else:
                        try:
                            external_data['splicingPredictions']['dbscSNVADA'] = "{:.2f}".format(float(record[14]))
                            internal_data['splicingPredictions']['dbscSNVADAColor'] = md_utilities.get_preditor_single_threshold_color(float(external_data['splicingPredictions']['dbscSNVADA']), 'dbscsnv')
                            if external_data['splicingPredictions']['dbscSNVADA'] != 'No match in dbscSNV v1.1':
                                splicing_radar_labels.append('dbscSNV ADA')
                                splicing_radar_values.append(external_data['splicingPredictions']['dbscSNVADA'])
                        except Exception:
                            # "score" is '.'
                            external_data['splicingPredictions']['dbscSNVADA'] = "No score for dbscSNV ADA {}".format(md_utilities.external_tools['dbscSNV']['version'])
                        try:
                            external_data['splicingPredictions']['dbscSNVRF'] = "{:.2f}".format(float(record[15]))
                            internal_data['splicingPredictions']['dbscSNVRFColor'] = md_utilities.get_preditor_single_threshold_color(float(external_data['splicingPredictions']['dbscSNVRF']), 'dbscsnv')
                            if external_data['splicingPredictions']['dbscSNVRF'] != 'No match in dbscSNV v1.1':
                                splicing_radar_labels.append('dbscSNV RF')
                                splicing_radar_values.append(external_data['splicingPredictions']['dbscSNVRF'])
                        except Exception:
                            # "score" is '.'
                            external_data['splicingPredictions']['dbscSNVRF'] = "No score for dbscSNV RF {}".format(md_utilities.external_tools['dbscSNV']['version'])
                        # dbscsnv_mpa_threshold = 0.8
                        if not external_data['overallPredictions']['mpaScore'] or \
                                external_data['overallPredictions']['mpaScore'] < 10:
                            if (isinstance(external_data['splicingPredictions']['dbscSNVADA'], float) and
                                float(external_data['splicingPredictions']['dbscSNVADA']) > md_utilities.predictor_thresholds['dbscsnv']) or \
                                (isinstance(external_data['splicingPredictions']['dbscSNVRF'], float) and
                                 float(external_data['splicingPredictions']['dbscSNVRF']) > md_utilities.predictor_thresholds['dbscsnv']):
                                external_data['overallPredictions']['mpaScore'] = 10
                                external_data['overallPredictions']['mpaImpact'] = 'High splice'
        internal_data['splicingPredictions']['splicingRadarLabels'] = splicing_radar_labels
        internal_data['splicingPredictions']['splicingRadarValues'] = splicing_radar_values
        # get classification info
        curs.execute(
            "SELECT a.acmg_class, a.class_date, a.comment, b.id, b.email, b.email_pref, b.username, c.html_code, c.acmg_translation \
                FROM class_history a, mobiuser b, valid_class c WHERE a.mobiuser_id = b.id AND a.acmg_class = c.acmg_class \
                AND a.variant_feature_id = %s ORDER BY a.class_date ASC",
            (variant_id,)
        )
        class_history = curs.fetchall()
        if len(class_history) == 0:
            class_history = None

        # MaxEntScan
        # we need to iterize through the wt and mt sequences to get
        # stretches of 23 nts for score3 and of 9 nts for score 5
        # then we create 2 NamedTemporaryFile to store the data
        # then run the perl scripts as subprocesses like this:
        # import subprocess
        # result = subprocess.run(['perl', 'score5.pl', 'test5'], stdout=subprocess.PIPE)
        # result.stdout
        # result is like
        # b'CAAATTCTG\t-17.88\nAAATTCTGC\t-13.03\nAATTCTGCA\t-35.61\nATTCTGCAA\t-22.21\nTTCTGCAAT\t-31.16\nTCTGCAATC\t-13.69\nCTGCAATCC\t-14.15\nTGCAATCCT\t-37.49\nGCAATCCTC\t-30.00\n'

        # iterate through scores and get the most likely to disrupt splicing
        # from Houdayer Humut 2012
        # "In every case, we recommend first‐line analysis with MES using a 15% cutoff."
        signif_scores5 = signif_scores3 = None
        # print(pos_splice_site )
        scores5wt, seq5wt_html = md_utilities.maxentscan(9, variant_features['variant_size'], variant_features['wt_seq'], 5)
        scores5mt, seq5mt_html = md_utilities.maxentscan(9, variant_features['variant_size'], variant_features['mt_seq'], 5)
        # scores5mt = md_utilities.maxentscan(9, variant_features['variant_size'], variant_features['mt_seq'], 5)
        signif_scores5 = md_utilities.select_mes_scores(
            re.split('\n', scores5wt),
            seq5wt_html,
            re.split('\n', scores5mt),
            seq5mt_html,
            0.15,
            3
        )
        if signif_scores5 == {}:
            signif_scores5 = None
        # 2 last numbers are variation cutoff to sign a significant change and absolute threshold to consider a score as interesting
        # print(signif_scores5)
        # ex
        # {5: ['CAGGTAATG', '9.43', 'CAGATAATG', '1.25', -654.4, 'CAG<span class="w3-text-red"><strong>G</strong></span>TAATG\n',\
        # '<strong>CAG</strong>gtaatg', 'CAG<span class="w3-text-red"><strong>A</strong></span>TAATG\n', '<strong>CAG</strong>ataatg']}
        if (variant_features['start_segment_type'] != 'exon') or \
                (external_data['positions']['nearestSsType'] == 'acceptor' and
                    external_data['positions']['nearestSsDist'] < 10):
            # exonic variants not near 3' ss don't require predictions for 3'ss
            scores3wt, seq3wt_html = md_utilities.maxentscan(23, variant_features['variant_size'], variant_features['wt_seq'], 3)
            scores3mt, seq3mt_html = md_utilities.maxentscan(23, variant_features['variant_size'], variant_features['mt_seq'], 3)
            signif_scores3 = md_utilities.select_mes_scores(
                re.split('\n', scores3wt),
                seq3wt_html,
                re.split('\n', scores3mt),
                seq3mt_html,
                0.15,
                3
            )
            if signif_scores3 == {}:
                signif_scores3 = None
            # print(signif_scores3)
        else:
            signif_scores3 = 'Not performed'
        external_data['splicingPredictions']['mes5'] = signif_scores5
        external_data['splicingPredictions']['mes3'] = signif_scores3
    else:
        close_db()
        if caller != 'browser':
            return jsonify(mobidetails_error='No such variant ID')
        else:
            return render_template(
                'md/unknown.html', run_mode=md_utilities.get_running_mode(), query="variant id: {}".format(variant_id)
            )
    close_db()
    if not external_data['overallPredictions']['mpaScore']:
        external_data['overallPredictions']['mpaScore'] = 0
        external_data['overallPredictions']['mpaImpact'] = 'unknown'
    else:
        internal_data['overallPredictions']['mpaColor'] = md_utilities.get_preditor_double_threshold_color(
            external_data['overallPredictions']['mpaScore'], 'mpa_mid', 'mpa_max'
        )
    if caller != 'browser':
        if caller == 'clispip':
            # we run spip here
            result_spip = md_utilities.run_spip(
                external_data['gene']['symbol'],
                external_data['gene']['RefSeqTranscript'],
                external_data['nomenclatures']['cName']
            )
            if result_spip == 'There has been an error while processing SPiP':
                external_data['splicingPredictions']['SPiP']['error'] = result_spip
            else:
                external_data['splicingPredictions']['SPiP'] = md_utilities.format_spip_result(result_spip, 'cli')
        # format json
        return jsonify(external_data)
    else:
        return render_template(
            'md/variant.html',
            run_mode=md_utilities.get_running_mode(),
            favourite=favourite, urls=md_utilities.urls,
            external_tools=md_utilities.external_tools,
            thresholds=md_utilities.predictor_thresholds,
            class_history=class_history,
            external_data=external_data,
            internal_data=internal_data
        )


# -------------------------------------------------------------------
# api - variant create


# @bp.route('/api/variant/create/<string:variant_chgvs>/<string:api_key>')
# def api_variant_create(variant_chgvs=None, api_key=None):
@bp.route('/api/variant/create', methods=['POST'])
def api_variant_create(variant_chgvs=None, caller=None, api_key=None):
    # get params
    caller = md_utilities.get_post_param(request, 'caller')
    variant_chgvs = md_utilities.get_post_param(request, 'variant_chgvs')
    api_key = md_utilities.get_post_param(request, 'api_key')
    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(
                mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.'
            )
        else:
            return redirect(url_for('md.index'), code=302)
    if variant_chgvs and \
            caller and \
            api_key:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # mobiuser_id = None
        res_check_api_key = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in res_check_api_key:
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']
        if md_utilities.check_caller(caller) == 'Invalid caller submitted':
            if caller == 'cli':
                return jsonify(mobidetails_error='Invalid caller submitted')
            else:
                flash('Invalid caller submitted to API.', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)

        variant_regexp = md_utilities.regexp['variant']
        match_object = re.search(
            rf'^([Nn][Mm]_\d+)\.(\d{{1,2}}):c\.({variant_regexp})',
            urllib.parse.unquote(variant_chgvs)
        )
        if match_object:
            # match_object = re.search(r'^([Nn][Mm]_\d+)\.(\d{1,2}):c\.(.+)', variant_chgvs)
            acc_no, submitted_nm_version, new_variant = match_object.group(1), match_object.group(2), match_object.group(3)
            # acc_no, acc_version, new_variant = match_object.group(1), match_object.group(2), match_object.group(3)
            new_variant = new_variant.replace(" ", "").replace("\t", "")
            # new_variant = new_variant.replace("\t", "")
            original_variant = new_variant
            curs.execute(
                "SELECT id FROM variant_feature WHERE c_name = %s AND gene_name[2] = %s",
                (new_variant, acc_no)
            )
            res = curs.fetchone()
            if res is not None:
                if caller == 'cli':
                    return jsonify(
                        mobidetails_id=res['id'],
                        url='{0}{1}'.format(
                            request.host_url[:-1],
                            url_for('api.variant', variant_id=res['id'], caller='browser')
                        )
                    )
                else:
                    return redirect(url_for('api.variant', variant_id=res['id'], caller='browser'), code=302)

            else:
                # creation
                # get gene
                curs.execute(
                    "SELECT name[1] as gene, nm_version FROM gene WHERE name[2] = %s and variant_creation = 'ok'",
                    (acc_no,)
                )
                res_gene = curs.fetchone()
                if res_gene is None:
                    if caller == 'cli':
                        return jsonify(
                            mobidetails_error='The gene corresponding to {} is not yet available for variant annotation in MobiDetails'.format(acc_no)
                        )
                    else:
                        flash(
                            'The gene corresponding to {} is not available for variant annotation in MobiDetails.'.format(acc_no),
                            'w3-pale-red'
                        )
                        return redirect(url_for('md.index'), code=302)
                if int(res_gene['nm_version']) != int(submitted_nm_version):
                    if caller == 'cli':
                        return jsonify(mobidetails_error='The RefSeq accession number submitted ({0}) for {1} does not match MobiDetail\'s ({2}).'.format(submitted_nm_version, acc_no, res_gene['nm_version']))
                    else:
                        flash('The RefSeq accession number submitted ({0}) for {1} does not match MobiDetail\'s ({2}).'.format(submitted_nm_version, acc_no, res_gene['nm_version']), 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
                acc_version = res_gene['nm_version']
                vv_base_url = md_utilities.get_vv_api_url()
                if not vv_base_url:
                    close_db()
                    if caller == 'cli':
                        return jsonify(mobidetails_error='Variant Validator looks down!')
                    else:
                        flash('Variant Validator looks down!', 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}.{2}:{3}/all?content-type=application/json".format(
                    vv_base_url, acc_no, acc_version, new_variant
                )
                vv_key_var = "{0}.{1}:c.{2}".format(acc_no, acc_version, new_variant)
                # http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                try:
                    vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
                except Exception:
                    close_db()
                    if caller == 'cli':
                        return jsonify(
                            mobidetails_error='Variant Validator did not return any value for the variant {}.'.format(new_variant)
                        )
                    else:
                        try:
                            flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                  The error is the following: {}'.format(vv_data['validation_warning_1']['validation_warnings']), 'w3-pale-red')
                        except Exception:
                            flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                  Sorry for the inconvenience. You may want to try again in a few minutes.', 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
                if re.search('[di][neu][psl]', new_variant):
                    # need to redefine vv_key_var for indels as the variant name returned
                    # by vv is likely to be different form the user's
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
                if 'mobidetails_error' in creation_dict:
                    if caller == 'cli':
                        return jsonify(creation_dict)
                    else:
                        flash(creation_dict['mobidetails_error'], 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
                if caller == 'cli':
                    return jsonify(creation_dict)
                else:
                    return redirect(url_for('api.variant', variant_id=creation_dict['mobidetails_id'], caller='browser'), code=302)
        else:
            if caller == 'cli':
                return jsonify(mobidetails_error='Malformed query {}'.format(urllib.parse.unquote(variant_chgvs)))
            else:
                flash('The query seems to be malformed: {}.'.format(urllib.parse.unquote(variant_chgvs)), 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
    else:
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameters')
        else:
            flash('The submitted parameters looks invalid!!!', 'w3-pale-red')
            return redirect(url_for('md.index'), code=302)

# -------------------------------------------------------------------
# api - variant create from genomic HGVS eg NC_000001.11:g.40817273T>G and gene name (HGNC)


# @bp.route('/api/variant/create_g/<string:variant_ghgvs>/<string:gene>/<string:caller>/<string:api_key>', methods=['GET', 'POST'])
# def api_variant_g_create(variant_ghgvs=None, gene=None, caller=None, api_key=None):
@bp.route('/api/variant/create_g', methods=['POST'])
def api_variant_g_create(variant_ghgvs=None, gene=None, caller=None, api_key=None):
    # get params
    # treat params one by one
    caller = md_utilities.get_post_param(request, 'caller')
    variant_ghgvs = md_utilities.get_post_param(request, 'variant_ghgvs')
    gene = md_utilities.get_post_param(request, 'gene_hgnc')
    api_key = md_utilities.get_post_param(request, 'api_key')

    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.')
        else:
            return redirect(url_for('md.index'), code=302)

    if variant_ghgvs and \
            gene and \
            caller and \
            api_key:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # mobiuser_id = None
        res_check_api_key = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in res_check_api_key:
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']

        if md_utilities.check_caller(caller) == 'Invalid caller submitted':
            if caller == 'cli':
                return jsonify(mobidetails_error='Invalid caller submitted')
            else:
                flash('Invalid caller submitted to API.', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)

        # check gene exists
        if re.search(r'^\d+$', gene):
            # HGNC id submitted
             curs.execute(
                "SELECT name, nm_version FROM gene WHERE hgnc_id = %s AND canonical = 't' and variant_creation = 'ok'",
                (gene,)
            )
        else:
            # search for gene name
            curs.execute(
                "SELECT name, nm_version FROM gene WHERE name[1] = %s AND canonical = 't' and variant_creation = 'ok'",
                (gene,)
            )
        res_gene = curs.fetchone()
        if res_gene:
            variant_regexp = md_utilities.regexp['variant']
            chrom_regexp = md_utilities.regexp['ncbi_chrom']
            # match_object = re.search(rf'^([Nn][Cc]_0000\d{{2}}\.\d{{1,2}}):g\.({variant_regexp})', urllib.parse.unquote(variant_ghgvs))
            match_object = re.search(rf'^({chrom_regexp}):g\.({variant_regexp})', urllib.parse.unquote(variant_ghgvs))
            if match_object:
                ncbi_chr, g_var = match_object.group(1), match_object.group(2)
                # 1st check hg38
                curs.execute(
                    "SELECT * FROM chromosomes WHERE ncbi_name = %s",
                    (ncbi_chr,)
                )
                res = curs.fetchone()
                if res:  # and \
                    #    res['genome_version'] == 'hg38':
                    genome_version, chrom = res['genome_version'], res['name']
                    # check if variant exists
                    # curs.execute(
                    #     "SELECT feature_id FROM variant WHERE genome_version = %s AND g_name = %s AND chr = %s",
                    #     (genome_version, g_var, chrom)
                    # )
                    curs.execute(
                        "SELECT b.feature_id FROM variant_feature a, variant b WHERE a.id = b.feature_id AND a.gene_name[1] = %s AND b.genome_version = %s AND b.g_name = %s AND b.chr = %s",
                        (gene, genome_version, g_var, chrom)
                    )
                    res = curs.fetchone()
                    if res:
                        if caller == 'cli':
                            return jsonify(
                                mobidetails_id=res['feature_id'],
                                url='{0}{1}'.format(
                                    request.host_url[:-1],
                                    url_for('api.variant', variant_id=res['feature_id'], caller='browser')
                                )
                            )
                        else:
                            return redirect(url_for('api.variant', variant_id=res['feature_id'], caller='browser'), code=302)
                    else:
                        # creation
                        vv_base_url = md_utilities.get_vv_api_url()
                        if not vv_base_url:
                            close_db()
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Variant Validator looks down!')
                            else:
                                flash('Variant Validator looks down!', 'w3-pale-red')
                                return redirect(url_for('md.index'), code=302)
                        genome_vv = 'GRCh38'
                        if genome_version == 'hg19':
                            genome_vv = 'GRCh37'
                            # weird VV seems to work better with 'GRCh37' than with 'hg19'
                        vv_url = "{0}VariantValidator/variantvalidator/{1}/{2}/all?content-type=application/json".format(
                            vv_base_url, genome_vv, variant_ghgvs
                        )
                        # print(vv_url)
                        # vv_key_var = "{0}.{1}:c.{2}".format(acc_no, acc_version, new_variant)
                        # http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                        try:
                            vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
                        except Exception:
                            close_db()
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Variant Validator did not return any value for the variant {}.'.format(urllib.parse.unquote(variant_ghgvs)))
                            else:
                                try:
                                    flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                          The error is the following: {}'.format(vv_data['validation_warning_1']['validation_warnings']), 'w3-pale-red')
                                except Exception:
                                    flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                          Sorry for the inconvenience. You may want to try again in a few minutes.', 'w3-pale-red')
                                return redirect(url_for('md.index'), code=302)
                        # look for gene acc #
                        # print(vv_data)
                        new_variant = None
                        vv_key_var = None
                        res_gene_non_can_list = []
                        # we still need a list of non canonical NM for the gene of interest
                        curs.execute(
                            "SELECT name, nm_version FROM gene WHERE name[1] = %s AND canonical = 'f'",
                            (gene,)
                        )
                        res_gene_non_can = curs.fetchall()
                        for transcript in res_gene_non_can:
                            res_gene_non_can_list.append('{0}.{1}'.format(transcript['name'][1], transcript['nm_version']))
                        for key in vv_data.keys():
                            variant_regexp = md_utilities.regexp['variant']
                            match_obj = re.search(rf'^([Nn][Mm]_\d+)\.(\d{{1,2}}):c\.({variant_regexp})', key)
                            if match_obj:
                                new_variant = match_obj.group(3)
                                # print("{0}-{1}-{2}-{3}".format(match_obj.group(1), res_gene['name'][1], match_obj.group(2), res_gene['nm_version']))
                                if match_obj.group(1) == res_gene['name'][1] and \
                                        str(match_obj.group(2)) == str(res_gene['nm_version']):
                                    # treat canonical as priority
                                    vv_key_var = "{0}.{1}:c.{2}".format(match_obj.group(1), match_obj.group(2), match_obj.group(3))
                                    break
                                elif not vv_key_var:
                                    # take into account non canonical isoforms
                                    # print('{0}.{1}'.format(match_obj.group(1), match_obj.group(2)))
                                    # print(res_gene_non_can_list)
                                    if '{0}.{1}'.format(match_obj.group(1), match_obj.group(2)) in res_gene_non_can_list:
                                        vv_key_var = "{0}.{1}:c.{2}".format(match_obj.group(1), match_obj.group(2), match_obj.group(3))
                        if vv_key_var:
                            # print(vv_key_var)
                            creation_dict = md_utilities.create_var_vv(
                                vv_key_var, res_gene['name'][0], res_gene['name'][1],
                                'c.{}'.format(new_variant), new_variant,
                                res_gene['nm_version'], vv_data, 'api', db, g
                            )
                            if caller == 'cli':
                                return jsonify(creation_dict)
                            else:
                                return redirect(url_for('api.variant', variant_id=creation_dict['mobidetails_id'], caller='browser'), code=302)
                        else:
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Could not create variant {} (possibly considered as intergenic or mapping on non-conventional chromosomes).'.format(urllib.parse.unquote(variant_ghgvs)), variant_validator_output=vv_data)
                            else:
                                try:
                                    flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                          The error is the following: {}'.format(vv_data['validation_warning_1']['validation_warnings']), 'w3-pale-red')
                                except Exception:
                                    flash('There has been a issue with the annotation of the variant via VariantValidator. \
                                          Sorry for the inconvenience. You may want to try again in a few minutes.', 'w3-pale-red')
                                return redirect(url_for('md.index'), code=302)

                else:
                    if caller == 'cli':
                        return jsonify(mobidetails_error='Unknown chromosome {} submitted or bad genome version (hg38 only)'.format(ncbi_chr))
                    else:
                        flash('The submitted chromosome or genome version looks corrupted (hg38 only).', 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
            else:
                if caller == 'cli':
                    return jsonify(mobidetails_error='Malformed query {}'.format(urllib.parse.unquote(variant_ghgvs)))
                else:
                    flash('The query seems to be malformed: {}.'.format(urllib.parse.unquote(variant_ghgvs)), 'w3-pale-red')
                    return redirect(url_for('md.index'), code=302)
        else:
            if caller == 'cli':
                return jsonify(mobidetails_error='The gene {} is currently not available for variant annotation in MobiDetails'.format(gene))
            else:
                flash('The gene {} is currently not available for variant annotation in MobiDetails'.format(gene), 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
    else:
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameters')
        else:
            flash('The submitted parameters looks invalid!!!', 'w3-pale-red')
            return redirect(url_for('md.index'), code=302)
# -------------------------------------------------------------------
# api - variant create from NCBI dbSNP rs id


@bp.route('/api/variant/create_rs', methods=['POST'])
def api_variant_create_rs(rs_id=None, caller=None, api_key=None):
    # get params
    caller = md_utilities.get_post_param(request, 'caller')
    rs_id = md_utilities.get_post_param(request, 'rs_id')
    api_key = md_utilities.get_post_param(request, 'api_key')
    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.')
        else:
            return redirect(url_for('md.index'), code=302)
    if rs_id and \
            caller and \
            api_key:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # check api key
        res_check_api_key = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in res_check_api_key:
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']
        # check caller
        if md_utilities.check_caller(caller) == 'Invalid caller submitted':
            if caller == 'cli':
                return jsonify(mobidetails_error='Invalid caller submitted')
            else:
                flash('Invalid caller submitted to the API.', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        # check rs_id
        trunc_rs_id = None
        match_obj = re.search(r'^rs(\d+)$', rs_id)
        if match_obj:
            trunc_rs_id = match_obj.group(1)
            # check if rsid exists
            curs.execute(
                "SELECT a.c_name, a.id, b.name[2] as nm, b.nm_version FROM variant_feature a, gene b WHERE a.gene_name = b.name AND a.dbsnp_id = %s",
                (trunc_rs_id,)
            )
            res_rs = curs.fetchall()
            if res_rs:
                vars_rs = {}
                for var in res_rs:
                    current_var = '{0}.{1}:c.{2}'.format(var['nm'], var['nm_version'], var['c_name'])
                    vars_rs[current_var] = {
                        'mobidetails_id': var['id'],
                        'url': '{0}{1}'.format(
                            request.host_url[:-1],
                            url_for('api.variant', variant_id=var['id'], caller='browser')
                        )
                    }
                if caller == 'cli':
                        return jsonify(vars_rs)
                else:
                    if len(res_rs) == 1:
                        return redirect(url_for('api.variant', variant_id=res_rs['id'], caller='browser'), code=302)
                    else:
                        return redirect(url_for('md.variant_multiple', vars_rs=vars_rs), code=302)
            # use putalyzer to get HGVS noemclatures
            # http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
            mutalyzer_url = "{0}getdbSNPDescriptions?rs_id={1}".format(
                md_utilities.urls['mutalyzer_api_json'], rs_id
            )
            # returns sthg like
            # ["NC_000011.10:g.112088901C>T", "NC_000011.9:g.111959625C>T", "NG_012337.3:g.7055C>T", "NM_003002.4:c.204C>T", "NM_003002.3:c.204C>T", "NM_001276506.2:c.204C>T", "NM_001276506.1:c.204C>T", "NR_077060.2:n.239C>T", "NR_077060.1:n.288C>T", "NM_001276504.2:c.87C>T", "NM_001276504.1:c.87C>T", "NG_033145.1:g.2898G>A"]
            try:
                mutalyzer_data = json.loads(http.request('GET', mutalyzer_url).data.decode('utf-8'))
            except Exception:
                close_db()
                if caller == 'cli':
                    return jsonify(mobidetails_error='Mutalyzer did not return any value for the variant {}.'.format(rs_id))
                else:
                    flash('Mutalyzer did not return any value for the variant {}'.format(rs_id), 'w3-pale-red')
                    return redirect(url_for('md.index'), code=302)
            # print(mutalyzer_data)
            md_response = {}
            # md_nm = list of NM recorded in MD, to be sure not to consider unexisting NM acc no
            # md_nm = []
            hgvs_nc = []
            gene_names = []
            # can_nm = None
            for hgvs in mutalyzer_data:  # works for exonic variants because mutalyzer returns no NM for intronic variants
                variant_regexp = md_utilities.regexp['variant']
                ncbi_chrom_regexp = md_utilities.regexp['ncbi_chrom']
                # intronic variant?
                # we need HGVS genomic to launch the API but also the gene - got from NG
                # f-strings usage https://stackoverflow.com/questions/6930982/how-to-use-a-variable-inside-a-regular-expression
                # https://www.python.org/dev/peps/pep-0498/
                match_nc = re.search(rf'^({ncbi_chrom_regexp}):g\.({variant_regexp})$', hgvs)
                # match_nc = re.search(rf'^(NC_0000\d{{2}}\.\d{{1,2}}):g\.({variant_regexp})$', hgvs)
                if match_nc:
                    # and \
                    #     not md_response:
                    # if hg38, we keep it in a variable that can be useful later
                    curs.execute(
                        "SELECT name, genome_version FROM chromosomes WHERE ncbi_name = %s",
                        (match_nc.group(1),)
                    )
                    res_chr = curs.fetchone()
                    if res_chr and \
                            res_chr['genome_version'] == 'hg38':
                        hgvs_nc.append(hgvs)
                        # look for gene name
                        positions = md_utilities.compute_start_end_pos(match_nc.group(2))
                        # print("SELECT a.name[1] as hgnc FROM gene a, segment b WHERE a.name = b.gene_name AND a.chr = {0} AND {1} BETWEEN SYMMETRIC # b.segment_start AND b.segment_end".format(res_chr['name'], positions[0]))
                        if not gene_names:
                            curs.execute(
                                "SELECT DISTINCT(a.name[1]) as hgnc FROM gene a, segment b WHERE a.name = b.gene_name AND b.genome_version = %s AND a.chr = %s AND %s BETWEEN SYMMETRIC b.segment_start AND b.segment_end",
                                (res_chr['genome_version'], res_chr['name'], positions[0])
                            )
                            res_gene = curs.fetchall()
                            if res_gene:
                                for hgnc_name in res_gene:
                                    gene_names.append(hgnc_name[0])
                else:
                    continue
            # do we have an intronic variant?
            if hgvs_nc and \
                    gene_names:  # and \
                    # not md_response:
                md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_g_create'))
                for var_hgvs_nc in hgvs_nc:
                    for gene_hgnc in gene_names:
                        data = {
                            'variant_ghgvs': urllib.parse.quote(var_hgvs_nc),
                            'gene_hgnc': gene_hgnc,
                            'caller': 'cli',
                            'api_key': api_key
                        }
                        try:
                            # print('{0}-{1}'.format(var_hgvs_nc, gene_hgnc))
                            md_response['{0};{1}'.format(var_hgvs_nc, gene_hgnc)] = json.loads(http.request('POST', md_api_url, headers=md_utilities.api_agent, fields=data).data.decode('utf-8'))
                        except Exception as e:
                            md_response['{0};{1}'.format(var_hgvs_nc, gene_hgnc)] = {'mobidetails_error': 'MobiDetails returned an unexpected error for your request {0}: {1}'.format(rs_id, var_hgvs_nc)}
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails API error',
                                    '<p>Error with MDAPI file writing for {0} ({1})<br /> - from {2} with args: {3}</p>'.format(
                                        rs_id,
                                        var_hgvs_nc,
                                        os.path.basename(__file__),
                                        e.args
                                    )
                                ),
                                '[MobiDetails - MDAPI Error]'
                            )
            if md_response:
                if caller == 'cli':
                    return jsonify(md_response)
                else:
                    if len(md_response) == 1:
                        for var in md_response:
                            if 'mobidetails_error' in md_response[var]:
                                flash(md_response[var]['mobidetails_error'], 'w3-pale-red')
                                return redirect(url_for('md.index'), code=302)
                            return redirect(url_for('api.variant', variant_id=md_response[var]['mobidetails_id'], caller='browser'), code=302)
                    else:
                        return render_template('md/variant_multiple.html', vars_rs=md_response)

            if caller == 'cli':
                return jsonify(mobidetails_error='Using Mutalyzer, we did not find any suitable variant corresponding to your request {}'.format(rs_id))
            else:
                flash('Using <a href="https://www.mutalyzer.nl/snp-converter?rs_id={0}", target="_blank">Mutalyzer</a>, we did not find any suitable variant corresponding to your request {0}'.format(rs_id), 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            if caller == 'cli':
                return jsonify(mobidetails_error='Invalid rs id provided')
            else:
                flash('Invalid rs id provided', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
    else:
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameter')
        else:
            flash('Invalid parameter', 'w3-pale-red')
            return redirect(url_for('md.index'), code=302)
            # return jsonify(mobidetails_error='Invalid rs id provided')


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
    if re.search(r'^\d+$', research):
        curs.execute(
            "SELECT * FROM gene WHERE hgnc_id = %s",
            (research,)
        )
    else:
        curs.execute(
            "SELECT * FROM gene WHERE name[%s] = %s",
            (search_id, research)
        )
    res = curs.fetchall()
    d_gene = {}
    if res:
        for transcript in res:
            if 'HGNC Name' not in d_gene:
                d_gene['HGNC Name'] = transcript['name'][0]
            if 'HGNC ID' not in d_gene:
                d_gene['HGNC ID'] = transcript['hgnc_id']
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
    if (md_utilities.get_running_mode() == 'maintenance'):
        return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot add new ACMG classes.')
    # get params
    variant_id = md_utilities.get_post_param(request, 'variant_id')
    acmg_id = md_utilities.get_post_param(request, 'acmg_id')
    api_key = md_utilities.get_post_param(request, 'api_key')
    # if request.args.get('variant_id') and \
    #         request.args.get('acmg_id') and \
    #         request.args.get('api_key'):
    #     variant_id = request.args.get('variant_id', type=int)
    #     acmg_id = request.args.get('acmg_id', type=int)
    #     api_key = request.args.get('api_key', type=str)
    # elif 'variant_id' in request.form and \
    #         'acmg_id' in request.form and \
    #         'api_key' in request.form:
    #     variant_id = request.form['variant_id']
    #     acmg_id = request.form['acmg_id']
    #     api_key = request.form['api_key']
    # else:
    #     return jsonify(mobidetails_error='I cannot fetch the right parameters')
    if variant_id and \
            acmg_id and \
            api_key:
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # mobiuser_id = None
        # check api key
        res_check_api_key = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in res_check_api_key:
            return jsonify(res_check_api_key)
        else:
            g.user = res_check_api_key['mobiuser']
        # if len(api_key) != 43:
        #     return jsonify(mobidetails_error='Invalid API key')
        # else:
        #     curs.execute(
        #         "SELECT * FROM mobiuser WHERE api_key = %s",
        #         (api_key,)
        #     )
        #     res = curs.fetchone()
        #     if res is None:
        #         return jsonify(mobidetails_error='Unknown API key')
        #     else:
        #         g.user = res
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
