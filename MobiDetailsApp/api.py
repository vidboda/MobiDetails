import re
import os
import gzip
from flask import (
    Blueprint, g, request, url_for, jsonify, redirect, flash, render_template
)
from markupsafe import escape
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

# -------------------------------------------------------------------
# api - check API key


@bp.route('/api/service/check_api_key', methods=['POST'])
def check_api_key(api_key=None):
    api_key = md_utilities.get_api_key_from_request(request)
    if not api_key:
        return jsonify(
            mobidetails_error='I cannot fetch the right parameters',
            api_key_pass_check=False,
            api_key_status='irrelevant'
        )
    db = get_db()
    response = md_utilities.check_api_key(db, api_key)
    if 'mobiuser' in response:
        close_db()
        if response['mobiuser']['activated'] is True:
            return jsonify(api_key_submitted=response['mobiuser']['api_key'] , api_key_pass_check=True, api_key_status='active')
        return jsonify(api_key_submitted=response['mobiuser']['api_key'] , api_key_pass_check=True, api_key_status='inactive')
    close_db()
    return jsonify(api_key_submitted=escape(api_key), api_key_pass_check=False, api_key_status='irrelevant')

# -------------------------------------------------------------------
# api - check which VV is running


@bp.route('/api/service/vv_instance', methods=['GET'])
def check_vv_instance():
    vv_url = md_utilities.get_vv_api_url()
    if vv_url:
        # if vv_url == md_utilities.urls['rest_vv_browser']:
        #     return jsonify(
        #         variant_validator_instance='Running internal VV server dedicated to web UI (can be used as a backup for API calls)',
        #         URL=vv_url
        #     )
        # elif vv_url == md_utilities.urls['rest_vv_api']:
        #     return jsonify(
        #         variant_validator_instance='Running internal VV server dedicated to API calls (can be used as a backup for web UI)',
        #         URL=vv_url
        #     )
        # elif vv_url == md_utilities.urls['rest_vv_genuine']:
        #     return jsonify(
        #         variant_validator_instance='Running genuine english VV server, as a backup - this means that both internal VV servers are down! Please warn me asap',
        #         URL=vv_url
        #     )


        if vv_url == md_utilities.urls['rest_vv_browser']['1']:
            return jsonify(
                variant_validator_instance='Running internal VV server dedicated to web UI (can be used as a backup for API calls)',
                URL=vv_url
            )
        elif vv_url == md_utilities.urls['rest_vv_browser']['2']:
            return jsonify(
                variant_validator_instance='Running internal VV server dedicated to API calls (can be used as a backup for web UI)',
                URL=vv_url
            )
        elif vv_url == md_utilities.urls['rest_vv_browser']['3']:
            return jsonify(
                variant_validator_instance='Running genuine english VV server, as a backup - this means that both internal VV servers are down! Please warn me asap',
                URL=vv_url
            )
        # restvv 2023 - comment all above
        # if vv_url == md_utilities.urls['rest_vv']['1']:
        #     return jsonify(
        #         variant_validator_instance='Running internal VV server dedicated to web UI (can be used as a backup for API calls)',
        #         URL=vv_url
        #     )
        # elif vv_url == md_utilities.urls['rest_vv']['2']:
        #     return jsonify(
        #         variant_validator_instance='Running genuine english VV server, as a backup - this means that both internal VV servers are down! Please warn me asap',
        #         URL=vv_url
        #     )
    return jsonify(
            variant_validator_instance='No VV running',
            URL='None'
        )


# -------------------------------------------------------------------
# api - variant exists?


@bp.route('/api/variant/exists/<string:variant_ghgvs>')
def api_variant_exists(variant_ghgvs=None):
    if variant_ghgvs is None:
        return jsonify(mobidetails_error='No variant submitted')
    variant_regexp = md_utilities.regexp['variant']
    chrom_regexp = md_utilities.regexp['ncbi_chrom']
    match_variant_ghgvs = re.search(rf'^({chrom_regexp}):g\.({variant_regexp})$', urllib.parse.unquote(variant_ghgvs))
    # match_object = re.search(r'^([Nn][Cc]_0000\d{2}\.\d{1,2}):g\.(.+)$', urllib.parse.unquote(variant_ghgvs))
    if match_variant_ghgvs:
        db = get_db()
        chrom, genome_version = md_utilities.get_common_chr_name(db, match_variant_ghgvs.group(1))
        if chrom and \
            genome_version:
            pattern = match_variant_ghgvs.group(2)
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT feature_id
                FROM variant
                WHERE chr = %s
                    AND g_name = %s
                    AND genome_version = %s
                """,
                (chrom, pattern, genome_version)
            )
            res = curs.fetchone()
            if res is not None:
                close_db()
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
                close_db()
                checked_var_ghgvs = '{0}:g.{1}'.format(match_variant_ghgvs.group(1), match_variant_ghgvs.group(2))
                return jsonify(mobidetails_warning='The variant {} does not exist yet in MD'.format(checked_var_ghgvs))
        else:
            return jsonify(mobidetails_error='The chromosome {} does not exist in MD'.format(match_variant_ghgvs.group(1)))
    else:
        return jsonify(mobidetails_error='Malformed query, please check your input')

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
    # browser sends 'dom.css.map'
    if api_key and \
            api_key != ',' and \
            len(api_key) == 43:
        res_check_api_key = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in res_check_api_key:
            close_db()
            if caller != 'browser':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        academic = res_check_api_key['mobiuser']['academic']
    # typically calling from webapp
    elif g.user:
        curs.execute(
            """
            SELECT *
            FROM mobiuser
            WHERE id = %s
            """,
            (g.user['id'],)
        )
        res_user = curs.fetchone()
        academic = res_user['academic']
    if not api_key:
        api_key = md_utilities.get_api_key(curs)

    # we need 2 dicts:
    # - one for data that will be presented to the world via the API: external_data
    # - a second one for data required for web pages presentation: internal_data
    external_data = {
        'variantId': None,
        'gene': {
            'symbol': None,
            'RefSeqTranscript': None,
            # 'RefSeqNg': None,
            'RefSeqNp': None,
            'ENST': None,
            'ENSP': None,
            'canonical': None,
            'MANE': None,
            'MANEPlusClinical': None,
            'RefSeqSelect': None,
            'previousSymbols_aliases': None,
            'hgncId': None,
            'chromosome': None,
            'strand': None,
            'numberOfExons': None,
            'hgncName': None,
            'proteinSize': None,
            'uniprotId': None,
            'clingenCriteriaSpec': None,
            'isOncogene': None,
            'isTumorSuppressor': None
        },
        'nomenclatures': {
            'cName': None,
            # 'ngName': None,
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
            'variantLocation': None,
        },
        'admin': {
            'creationDate': None,
            'creationUserName': None,
        },
        'frequenciesDatabases': {
            # 'gnomADv2Exomehg19': None,
            # 'gnomADv2Genomehg19': None,
            'gnomADv2Exome': None,
            'gnomADv2Genome': None,
            'gnomADv2ExomeNonCancer': None,
            'gnomADv2GenomeNonCancer': None,
            'gnomADv3': None,
            'gnomADv4Genome': None,
            'gnomADv4Exome': None,
            'dbSNPrsid': None,
            'clinvarId': None,
            'clinvarClinsigConf': None,
            'clinvarClinsig': None,
            'clinvarClinRevStat': None,
            'clinvarOncConf': None,
            'clinvarOnc': None,
            'clinvarOncRevStat': None,
            'clinvarSci': None,
            'clinvarSciRevStat': None,
        },
        'overallPredictions': {
            'caddRaw': None,
            'caddPhred': None,
            'eigenRaw': None,
            'eigenPhred': None,
            'mpaScore': None,
            'mpaImpact': None,
            'gpnmsa': None,
            'cactus241way': None,
            'phylop_primates': None
        },
        'nonCodingPredictions':{
            'mobideep': None,
            'promoterai': None,
            'remm': None,
        },
        'functionalStudies':{
            'mavedb_score': None,
            'mavedb_prot': None,
            'mavedb_urn': None,
            'mavedb_var_urn': None
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
            'abSplice': {}
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
            'amScore': None,
            'amPred': None,
            'bayesDelScore': None,
            'bayesDelPred': None,
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
            'fathmmxfScore': None,
            'fathmmxfPred': None,
            'proveanScore': None,
            'proveanPred': None,
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
        'morfeedb': [{
            'orfSNVs_type': None,
            'orfSNVs_frame': None,
            'type_of_generated_ORF': None,
            'Ratio_length_pred_obs': None,
            'TIS_sequence': None,
            'STOP_sequence': None,
            'Kozak_sequence': None,
            'Kozak_score': None,
            'Kozak_strength': None,
            'TIS_c_pos': None,
            'STOP_c_pos': None,
        }]
    }
    internal_data = {
        'admin': {
            'creationUser': None,
            'creationUserEmailPref': None,
            'otherIds': None,
            'mappedCanonical': None,
            'transcript_road_signs': None,
            'apiKey': api_key
        },
        'nomenclatures': {
            'cName': None,
            'pName': None,
            'oneLetterpName': None
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
            'gpnmsaColor': None,
            'phylop_primatesColor': None,
            'cactus241wayColor': None,
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
            'spliceai_warning': None,
            'abSpliceResults': None,
            'abSpliceMaxColor': None,
            'abspliceDNAHeader': [],
            'abspliceDNAValues': [],
        },
        'positions': {
            'metaDomeColor': None,
            'distFromExon': None,
            'substitutionNature': None,
            'neighbourExonNumber': None,
            'insSize': None,
            'locationMobiDeepGraph': None,
        },
        'missensePredictions': {
            'amColor': None,
            'bayessDelStar': None,
            'bayesDelColor': None,
            'siftStar': None,
            'siftColor': None,
            'polyphen2HdivStar': None,
            'polyphen2HdivColor': None,
            'polyphen2HvarStar': None,
            'polyphen2HvarColor': None,
            'fathmmxfStar': None,
            'fathmmxfColor': None,
            # 'fathmmMklStar': None,
            # 'fathmmMklColor': None,
            'proveanStar': None,
            'lrtStar': None,
            'mutationTasterStar': None,
            'clinpredStar': None,
            'clinpredColor': None,
            'revelStar': None,
            'amStar': None,
            'metaSVMColor': None,
            'metaLRColor': None,
            'misticColor': None,
        },
        'nonCodingPredictions': {
            'remmColor': None,
            'promoteraiColor': None,
        },
        'episignature': {
            'referenceArticle': None,
            'pubmedID': None,
            'DNAMethylationPattern': None,
            'Description': None,
            'ExpertACMGClassification': None,
            'ACMGTranslation': None,
            'htmlCode': None
        },
        'noMatch': {
            'abSplice': None,
            'cadd': None,
            'eigen': None,
            'dbnsfp': None,
            'dbmts': None,
            'spliceai': None,
            'episignature': None,
            'mavedb': None,
            'morfeedb': None,
            'gpnmsa': None,
            'cactus241way': None,
            'remm': None,
            'mavedb': None,
            'mobideep': None,
            'phylop_primates': None,
            'promoterai': None
        }
    }
    # First, query to determine whether the vairant is genic or not:
    var_type = 'genic'
    curs.execute(
        """
        SELECT c_name
        FROM variant_feature
        WHERE id = %s
        """,
        (variant_id,)
    )
    variant_c_name = curs.fetchone()
    if variant_c_name['c_name'] is None:
        var_type = 'intergenic'
        # get all variant_features and gene info
        curs.execute(
            """
            SELECT a.*, a.id as var_id, c.id AS mobiuser_id, c.email, c.username, c.email_pref
            FROM variant_feature a, mobiuser c
            WHERE a.creation_user = c.id
                AND a.id = %s
            """,
            (variant_id,)
        )
    else:
        # get all variant_features and gene info
        curs.execute(
            """
            SELECT a.*, b.*, a.id as var_id, c.id AS mobiuser_id, c.email, c.username, c.email_pref, d.so_accession
            FROM variant_feature a, gene b, mobiuser c, valid_prot_type d
            WHERE a.gene_symbol = b.gene_symbol
                AND a.refseq = b.refseq
                AND a.creation_user = c.id
                AND a.prot_type = d.prot_type
                AND a.id = %s
            """,
            (variant_id,)
        )
    variant_features = curs.fetchone()
    # print(variant_features)
    if variant_features:
        if var_type == 'genic':
            # get MANE info
            # query below just to get the correct format for the sub below
            curs.execute(
                """
                SELECT refseq
                FROM gene
                WHERE gene_symbol = %s
                ORDER BY number_of_exons DESC
                """,
                (variant_features['gene_symbol'],)
            )  # get all isoforms
            result_all_genes = curs.fetchall()
            transcript_road_signs = md_utilities.get_transcript_road_signs(variant_features['gene_symbol'], result_all_genes)
            if not 'error' in transcript_road_signs and \
                    variant_features['refseq'] in transcript_road_signs:
                external_data['gene']['MANE'] = transcript_road_signs[variant_features['refseq']]['mane_select']
                external_data['gene']['MANEPlusClinical'] = transcript_road_signs[variant_features['refseq']]['mane_plus_clinical']
                external_data['gene']['RefSeqSelect'] = transcript_road_signs[variant_features['refseq']]['refseq_select']
            # length of c_name for printing on screen
            var_cname = variant_features['c_name']
            if len(var_cname) > 30:
                match_obj = re.search(r'(.+ins)[ATGC]+$', var_cname)
                if match_obj:
                    var_cname = match_obj.group(1)

        # fill in dicts
        external_data['variantId'] = variant_features['var_id']
        if var_type == 'genic':
            external_data['nomenclatures']['cName'] = 'c.{}'.format(variant_features['c_name'])
            external_data['nomenclatures']['ivsName'] = variant_features['ivs_name']
            external_data['nomenclatures']['pName'] = 'p.{}'.format(variant_features['p_name'])
             # for HTML webpages
            internal_data['nomenclatures']['cName'] = var_cname
            # internal_data['nomenclatures']['ngName'] = variant_features['ng_name']
            internal_data['nomenclatures']['pName'] = variant_features['p_name']
            internal_data['nomenclatures']['oneLetterpName'] = md_utilities.three2one_fct(variant_features['p_name'])
            external_data['gene']['symbol'] = variant_features['gene_symbol']
            external_data['gene']['RefSeqTranscript'] = variant_features['refseq']
            # external_data['gene']['RefSeqNg'] = variant_features['ng']
            external_data['gene']['RefSeqNp'] = variant_features['np']
            external_data['gene']['ENST'] = variant_features['enst']
            external_data['gene']['ENSP'] = variant_features['ensp']
            external_data['gene']['canonical'] = variant_features['canonical']
            external_data['gene']['previousSymbols_aliases'] = variant_features['second_name']
            external_data['gene']['hgncId'] = variant_features['hgnc_id']
            external_data['gene']['chromosome'] = variant_features['chr']
            external_data['gene']['strand'] = variant_features['strand']
            external_data['gene']['numberOfExons'] = variant_features['number_of_exons']
            external_data['gene']['hgncName'] = variant_features['hgnc_name']
            external_data['gene']['proteinSize'] = variant_features['prot_size']
            external_data['gene']['uniprotId'] = variant_features['uniprot_id']
            # get clingen spec
            external_data['gene']['clingenCriteriaSpec'] = md_utilities.get_clingen_criteria_specification_id(external_data['gene']['symbol'])
            # get oncoKB data
            oncokb_info = md_utilities.get_oncokb_genes_info(external_data['gene']['symbol'])
            external_data['gene']['isOncogene'] = oncokb_info['is_oncogene']
            external_data['gene']['isTumorSuppressor'] = oncokb_info['is_tumor_suppressor']
            external_data['positions']['proteinType'] = variant_features['prot_type']
            external_data['positions']['proteinTypeSoAccession'] = variant_features['so_accession']
            external_data['positions']['segmentStartType'] = variant_features['start_segment_type']
            external_data['positions']['segmentStartNumber'] = variant_features['start_segment_number']
            external_data['positions']['segmentEndType'] = variant_features['end_segment_type']
            external_data['positions']['segmentEndNumber'] = variant_features['end_segment_number']
            external_data['positions']['variantLocation'] = md_utilities.get_var_genic_csq(variant_features['c_name'])
            # convert into mobideep Charts.js position in graph [0-4] or None for exons
            # internal_data['positions']['locationMobiDeepGraph'] = md_utilities.mobideepGraphPosition[external_data['positions']['variantLocation']]
        else:
            external_data['positions']['variantLocation']  = 'intergenic'
        # convert into mobideep Charts.js position in graph [0-5] or None for exons
        internal_data['positions']['locationMobiDeepGraph'] = md_utilities.mobideepGraphPosition[external_data['positions']['variantLocation']]


        external_data['sequences']['wildType'] = variant_features['wt_seq']
        external_data['sequences']['mutant'] = variant_features['mt_seq']
        external_data['positions']['DNAType'] = variant_features['dna_type']
        external_data['positions']['RNAType'] = variant_features['rna_type']
        external_data['positions']['size'] = variant_features['variant_size']
        external_data['admin']['creationDate'] = variant_features['creation_date']
        internal_data['admin']['creationUser'] = variant_features['mobiuser_id']
        internal_data['admin']['creationUserEmailPref'] = variant_features['email_pref']
        external_data['admin']['creationUserName'] = variant_features['username']

        external_data['frequenciesDatabases']['dbSNPrsid'] = 'rs{}'.format(variant_features['dbsnp_id'])
        internal_data['frequenciesDatabases']['dbSNPrsid'] = variant_features['dbsnp_id']

        # get variant info
        curs.execute(
            """
            SELECT *
            FROM variant
            WHERE feature_id = %s
            """,
            (variant_id,)
        )
        variant = curs.fetchall()
        
        if variant_features['dna_type'] == 'indel' \
                or variant_features['dna_type'] == 'insertion':
            match_obj = re.search(r'ins([ATGC]+)$', variant[0]['g_name'])
            if match_obj:
                internal_data['positions']['insSize'] = len(match_obj.group(1))

        aa_pos = None
        # pos_splice_site = None
        domain = None
        favourite = None
        if g.user:
            # favourite var?
            curs.execute(
                """
                SELECT type
                FROM mobiuser_favourite
                WHERE feature_id = %s
                    AND mobiuser_id = %s
                """,
                (variant_id, g.user['id'])
            )
            favourite = curs.fetchone()

        splicing_radar_labels = []
        splicing_radar_values = []
        other_ids = None
        for var in variant:
            if var['genome_version'] == 'hg38':
                res_chr = md_utilities.get_ncbi_chr_name(db, 'chr{0}'.format(var['chr']), var['genome_version'])
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
                if var_type == 'genic':
                    # same variant mapped on other isoforms
                    curs.execute(
                        """
                        SELECT a.feature_id, b.gene_symbol, b.refseq, b.c_name, c.canonical
                        FROM variant a, variant_feature b, gene c
                        WHERE a.feature_id = b.id
                            AND b.gene_symbol = c.gene_symbol
                            AND b.refseq = c.refseq
                            AND a.chr = %s
                            AND pos = %s
                            AND a.pos_ref = %s
                            AND a.pos_alt = %s
                            AND a.genome_version  = 'hg38'
                            AND a.feature_id <> %s
                        """,
                        (
                            external_data['VCF']['chr'],
                            external_data['VCF']['hg38']['pos'],
                            external_data['VCF']['hg38']['ref'],
                            external_data['VCF']['hg38']['alt'],
                            variant_id
                        )
                    )
                    res_ids = curs.fetchall()
                    mapped_canonical = True if external_data['gene']['canonical'] is True else False
                    if res_ids:
                        if not 'error' in transcript_road_signs:
                            internal_data['admin']['transcript_road_signs'] = transcript_road_signs
                        internal_data['admin']['otherIds'] = res_ids
                        other_ids = [res_id['feature_id'] for res_id in res_ids]
                        for res_id in res_ids:
                            if mapped_canonical is False and \
                                    res_id['canonical'] is True:
                                mapped_canonical = True
                    if mapped_canonical is False:
                        # get canonical iso
                        curs.execute(
                            """
                            SELECT refseq as canonical
                            FROM gene
                            WHERE gene_symbol = %s
                                AND canonical = 't'
                            """,
                            (external_data['gene']['symbol'],)
                        )
                        res_canon = curs.fetchone()
                        if res_canon:
                            internal_data['admin']['mappedCanonical'] = res_canon['canonical']
                    # episignature
                    # if this developps, need to identify target genes
                    if variant_features['gene_symbol'] == 'KMT2A':
                        record = md_utilities.get_value_from_tabix_file(
                            'EpiSign',
                            md_utilities.local_files['episignature']['abs_path'],
                            var,
                            variant_features
                        )
                        if isinstance(record, str):
                            internal_data['noMatch']['episignature'] = 'No match in EpiSIgn'
                        else:
                            internal_data['episignature']['referenceArticle'] = record[int(md_utilities.external_tools['EpiSignature']['referenceArticle_value_col'])]
                            internal_data['episignature']['pubmedID'] = record[int(md_utilities.external_tools['EpiSignature']['pubmedID_value_col'])]
                            internal_data['episignature']['DNAMethylationPattern'] = record[int(md_utilities.external_tools['EpiSignature']['DNA_methylation_pattern_value_col'])]
                            internal_data['episignature']['Description'] = record[int(md_utilities.external_tools['EpiSignature']['Description'])]
                            internal_data['episignature']['ExpertACMGClassification'] = record[int(md_utilities.external_tools['EpiSignature']['expert_ACMG_classification_value_col'])]
                            curs.execute(
                                """
                                SELECT html_code, acmg_translation \
                                FROM valid_class \
                                WHERE acmg_class = %s
                                """,
                                (internal_data['episignature']['ExpertACMGClassification'],)
                            )
                            res_code = curs.fetchone()
                            internal_data['episignature']['ACMGTranslation'] = res_code['acmg_translation']
                            internal_data['episignature']['htmlCode'] = res_code['html_code']
                            # print(internal_data['episignature'])
                    # compute position / splice sites
                    if variant_features['variant_size'] < 50 and \
                            variant_features['start_segment_type'] == 'exon':
                        # we want exon start and end
                        positions = md_utilities.get_positions_dict_from_vv_json(
                            external_data['gene']['symbol'],
                            external_data['gene']['RefSeqTranscript'],
                            external_data['VCF']['hg38']['ncbiChr'],
                            str(external_data['positions']['segmentStartNumber'])
                        )
                        if isinstance(positions, str):
                            # error
                            close_db()
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Error in retrieving the exon genomic positions')
                            else:
                                flash(
                                    """
                                    Error in retrieving the exon genomic positions. An admin has been warned.
                                    """,
                                    'w3-pale-red'
                                )
                                md_utilities.send_error_email(
                                    md_utilities.prepare_email_html(
                                        'MobiDetails API error',
                                        '<p>Error with MDAPI exon definition for variant {0}'.format(variant_id)
                                    ),
                                    '[MobiDetails - MDAPI Error]'
                                )
                                return redirect(url_for('md.index'), code=302)

                        # get info to build hexoSplice link
                        if variant_features['dna_type'] == 'substitution':
                            internal_data['hexosplice']['exonSequence'] = md_utilities.get_exon_sequence(
                                positions, var['chr'], variant_features['strand']
                            )
                            internal_data['hexosplice']['exonFirstNtCdnaPosition'] = md_utilities.get_exon_first_nt_cdna_position(
                                positions, var['pos'], variant_features['c_name']
                            )
                            if internal_data['hexosplice']['exonFirstNtCdnaPosition'] < 1:
                                internal_data['positions']['substitutionNature'] = md_utilities.get_substitution_nature(
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
                                """
                                SELECT * FROM uniprot_domain \
                                WHERE uniprot_id = '{0}' \
                                    AND (('{1}' BETWEEN aa_start AND aa_end) \
                                    OR ('{2}' BETWEEN aa_start AND aa_end))
                                """.format(
                                    variant_features['uniprot_id'], aa_pos[0], aa_pos[1]
                                )
                            )
                            domains = curs.fetchall()
                            for domain in domains:
                                external_data['positions']['proteinDomain'].append([urllib.parse.unquote(domain['name']), domain['aa_start'], domain['aa_end']])

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
                        positions_neighb_exon = md_utilities.get_positions_dict_from_vv_json(
                            external_data['gene']['symbol'],
                            external_data['gene']['RefSeqTranscript'],
                            external_data['VCF']['hg38']['ncbiChr'],
                            internal_data['positions']['neighbourExonNumber']
                        )
                        if isinstance(positions_neighb_exon, str):
                            # error
                            close_db()
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Error in retrieving the exon genomic positions')
                            else:
                                flash(
                                    """
                                    Error in retrieving the exon genomic positions. An admin has been warned.
                                    """,
                                    'w3-pale-red'
                                )
                                md_utilities.send_error_email(
                                    md_utilities.prepare_email_html(
                                        'MobiDetails API error',
                                        '<p>Error with MDAPI exon definition for variant {0}'.format(variant_id)
                                    ),
                                    '[MobiDetails - MDAPI Error]'
                                )
                                return redirect(url_for('md.index'), code=302)
                        if sign == '+':
                            internal_data['canvas']['preceedingSegmentType'] = None
                            internal_data['canvas']['preceedingSegmentNumber'] = None
                            internal_data['canvas']['followingSegmentType'] = 'intron'
                            internal_data['canvas']['followingSegmentNumber'] = variant_features['start_segment_number']
                            (internal_data['splicingPredictions']['nat5ssScore'], internal_data['splicingPredictions']['nat5ssSeq']) = md_utilities.get_maxent_natural_sites_scores(
                                var['chr'], external_data['gene']['strand'], 5, positions_neighb_exon
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
                record = md_utilities.get_value_from_tabix_file(
                    'Clinvar', md_utilities.local_files['clinvar_hg38']['abs_path'], var, variant_features
                )
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['clinvarClinsig'] = "{0} {1}".format(record, md_utilities.external_tools['ClinVar']['version'])
                else:
                    external_data['frequenciesDatabases']['clinvarId'] = record[2]
                    # https://github.com/ncbi/clinvar/tree/master/sample_tab_delimited
                    # https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/
                    ##INFO=<ID=ONC,Number=.,Type=String,Description="Aggregate oncogenicity classification for this single variant; multiple values are separated by a vertical bar">
                    ##INFO=<ID=ONCREVSTAT,Number=.,Type=String,Description="ClinVar review status of oncogenicity classification for the Variation ID">
                    ##INFO=<ID=ONCCONF,Number=.,Type=String,Description="Conflicting oncogenicity classification for this single variant; multiple values are separated by a vertical bar">
                    ##INFO=<ID=SCIREVSTAT,Number=.,Type=String,Description="ClinVar review status of somatic clinical impact for the Variation ID">
                    ##INFO=<ID=SCI,Number=.,Type=String,Description="Aggregate somatic clinical impact for this single variant; multiple values are separated by a vertical bar">
                    # germline
                    pattern = r'([^=;]+)=([^;]+)'
                    matches = re.findall(pattern, record[7])
                    dict_values = {cle: valeur for cle, valeur in matches}

                    external_data['frequenciesDatabases']['clinvarClinsig'] = dict_values["CLNSIG"].replace('_', ' ') if "CLNSIG" in dict_values else None
                    external_data['frequenciesDatabases']['clinvarClinsigConf'] = dict_values["CLNSIGCONF"].replace('%3B', '-') if "CLNSIGCONF" in dict_values else None
                    external_data['frequenciesDatabases']['clinvarOnc'] = dict_values["ONC"].replace('_', ' ') if "ONC" in dict_values else None
                    external_data['frequenciesDatabases']['clinvarOncRevStat'] = dict_values["ONCREVSTAT"] if "ONCREVSTAT" in dict_values else None
                    external_data['frequenciesDatabases']['clinvarOncConf'] = dict_values["ONCCONF"] if "ONCCONF" in dict_values else None
                    external_data['frequenciesDatabases']['clinvarSci'] = dict_values["SCI"].replace('_', ' ') if "SCI" in dict_values else None
                    external_data['frequenciesDatabases']['clinvarSciRevStat'] = dict_values["SCIREVSTAT"] if "SCIREVSTAT" in dict_values else None

                    for i in ['clinvarClinsig', 'clinvarOnc', 'clinvarSci']:
                        if external_data['frequenciesDatabases'][i] == 'no_classification_for_the_single_variant':
                            external_data['frequenciesDatabases'][i] = 'No classification for the single variant'

                    # define stars
                    for revstat in md_utilities.clinvar_review_status:
                        if re.search(rf'CLNREVSTAT={revstat};', record[7]):
                            external_data['frequenciesDatabases']['clinvarClinRevStat'] = md_utilities.clinvar_review_status[revstat]
                        elif re.search(rf'ONCREVSTAT={revstat};', record[7]):
                            external_data['frequenciesDatabases']['clinvarOncRevStat'] = md_utilities.clinvar_review_status[revstat]
                        elif re.search(rf'SCIREVSTAT={revstat};', record[7]):
                            external_data['frequenciesDatabases']['clinvarSciRevStat'] = md_utilities.clinvar_review_status[revstat]
                    # MPA score
                    if external_data['frequenciesDatabases']['clinvarClinsig'] and \
                            re.search('pathogenic', external_data['frequenciesDatabases']['clinvarClinsig'], re.IGNORECASE) and \
                            not re.search('pathogenicity', external_data['frequenciesDatabases']['clinvarClinsig'], re.IGNORECASE):
                        external_data['overallPredictions']['mpaScore'] = 10
                        external_data['overallPredictions']['mpaImpact'] = 'Clinvar pathogenic'
                if var_type == 'genic':
                    # MPA PTC
                    if not external_data['overallPredictions']['mpaScore'] or \
                            external_data['overallPredictions']['mpaImpact'] != 'Clinvar pathogenic':
                        if variant_features['prot_type'] == 'nonsense' or \
                                variant_features['prot_type'] == 'frameshift':
                            external_data['overallPredictions']['mpaScore'] = 10
                            external_data['overallPredictions']['mpaImpact'] = variant_features['prot_type']
                # gnomadv2 ex + non cancer
                record = md_utilities.get_value_from_tabix_file('gnomAD exome', md_utilities.local_files['gnomad_exome_hg38']['abs_path'], var, variant_features)
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['gnomADv2Exome'] = record
                    external_data['frequenciesDatabases']['gnomADv2ExomeNonCancer'] = record
                else:
                    external_data['frequenciesDatabases']['gnomADv2Exome'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                    external_data['frequenciesDatabases']['gnomADv2ExomeNonCancer'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_noncancer_col'])]
                # gnomadv2 ge + non cancer
                if external_data['gene']['chromosome'] != 'Y':
                    record = md_utilities.get_value_from_tabix_file('gnomAD genome', md_utilities.local_files['gnomad_genome_hg38']['abs_path'], var, variant_features)
                    if isinstance(record, str):
                        external_data['frequenciesDatabases']['gnomADv2Genome'] = record
                        external_data['frequenciesDatabases']['gnomADv2GenomeNonCancer'] = record
                    else:
                        # print(record)
                        external_data['frequenciesDatabases']['gnomADv2Genome'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                        external_data['frequenciesDatabases']['gnomADv2GenomeNonCancer'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_noncancer_col'])]
                # gnomadv4 genome
                record = md_utilities.get_value_from_tabix_file(
                    'gnomADv4 Genome', md_utilities.local_files['gnomad_4_genome']['abs_path'], var, variant_features
                )
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['gnomADv4Genome'] = record
                else:
                    external_data['frequenciesDatabases']['gnomADv4Genome'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                # gnomadv4 exome
                record = md_utilities.get_value_from_tabix_file(
                    'gnomADv4 Exome', md_utilities.local_files['gnomad_4_exome']['abs_path'], var, variant_features
                )
                if isinstance(record, str):
                    external_data['frequenciesDatabases']['gnomADv4Exome'] = record
                else:
                    external_data['frequenciesDatabases']['gnomADv4Exome'] = record[int(md_utilities.external_tools['gnomAD']['annovar_format_af_col'])]
                # dbNSFP and others
                # if variant_features['prot_type'] == 'missense':
                if var_type == 'genic':
                    record = md_utilities.get_value_from_tabix_file(
                        'dbnsfp', md_utilities.local_files['dbnsfp']['abs_path'], var, variant_features
                    )
                    # Eigen
                    try:
                        external_data['overallPredictions']['eigenRaw'] = format(float(record[int(md_utilities.external_tools['Eigen']['dbNSFP_value_col'])]), '.2f')
                        external_data['overallPredictions']['eigenPhred'] = format(float(record[int(md_utilities.external_tools['Eigen']['dbNSFP_pred_col'])]), '.2f')
                    except Exception:
                        internal_data['noMatch']['eigen'] = 'No match in dbNSFP for Eigen'
                    if 'eigenRaw' in external_data['overallPredictions'] and \
                            external_data['overallPredictions']['eigenRaw'] == '.':
                        internal_data['noMatch']['eigen'] = 'No score in dbNSFP for Eigen'
                    # record comes from Eigen section above
                    if variant_features['prot_type'] == 'missense':
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
                            # fathmm-XF - replaces fathmm in dbNSFP v5
                            external_data['missensePredictions']['fathmmxfScore'], external_data['missensePredictions']['fathmmxfPred'], internal_data['missensePredictions']['fathmmStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.external_tools['FatHMM-XF']['dbNSFP_value_col']), int(md_utilities.external_tools['FatHMM-XF']['dbNSFP_pred_col']), ';', 'basic', -0.1, 'gt', record
                            )
                            external_data['missensePredictions']['fathmmxfScore'] = format(float(external_data['missensePredictions']['fathmmxfScore']), '.3f')
                            internal_data['missensePredictions']['fathmmxfColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['fathmmxfScore'], 'fathmmxf')
                            if external_data['missensePredictions']['fathmmxfPred'] == 'Damaging':
                                mpa_missense += 1
                            if external_data['missensePredictions']['fathmmxfPred'] != 'no prediction':
                                mpa_avail += 1
                            # fathmm-mkl -- not displayed - removed from dbNSFP v5
                            # external_data['missensePredictions']['fathmmMklScore'], external_data['missensePredictions']['fathmmMklPred'], internal_data['missensePredictions']['fathmmMklStar'] = md_utilities.getdbNSFP_results(
                            #     transcript_index, int(md_utilities.hidden_external_tools['FatHMM-MKL']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['FatHMM-MKL']['dbNSFP_pred_col']), ';', 'basic', 20, 'lt', record
                            # )

                            # internal_data['missensePredictions']['fathmmMklColor'] = md_utilities.get_preditor_single_threshold_reverted_color(external_data['missensePredictions']['fathmmMklScore'], 'fathmm-mkl')
                            # if external_data['missensePredictions']['fathmmMklPred'] == 'Damaging':
                            #     mpa_missense += 1
                            # if external_data['missensePredictions']['fathmmMklPred'] != 'no prediction':
                            #     mpa_avail += 1
                            # provean -- not displayed
                            external_data['missensePredictions']['proveanScore'], external_data['missensePredictions']['proveanPred'], internal_data['missensePredictions']['proveanStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.hidden_external_tools['Provean']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['Provean']['dbNSFP_pred_col']), ';', 'basic', 20, 'lt', record
                            )
                            if external_data['missensePredictions']['proveanPred'] == 'Damaging':
                                mpa_missense += 1
                            if external_data['missensePredictions']['proveanPred'] != 'no prediction':
                                mpa_avail += 1
                            # BayesDel
                            external_data['missensePredictions']['bayesDelScore'], external_data['missensePredictions']['bayesDelPred'], internal_data['missensePredictions']['bayesDelStar'] = md_utilities.getdbNSFP_results(
                                transcript_index, int(md_utilities.external_tools['BayesDel']['dbNSFP_value_col']), int(md_utilities.external_tools['BayesDel']['dbNSFP_pred_col']), ';', 'basic', -2, 'lt', record
                            )
                            external_data['missensePredictions']['bayesDelScore'] = format(float(external_data['missensePredictions']['bayesDelScore']), '.3f')
                            # threshold for bayesdel does not follow dbNSFP, see md_resources
                            if (float(external_data['missensePredictions']['bayesDelScore']) < float(md_utilities.predictor_thresholds['bayesdel'])):
                                external_data['missensePredictions']['bayesDelPred'] = 'Tolerated'
                            internal_data['missensePredictions']['bayesDelColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['bayesDelScore'], 'bayesdel')
                            # LRT -- not displayed removed in dbNSFP v5
                            # external_data['missensePredictions']['lrtScore'], external_data['missensePredictions']['lrtPred'], internal_data['missensePredictions']['lrtStar'] = md_utilities.getdbNSFP_results(
                            #     transcript_index, int(md_utilities.hidden_external_tools['LRT']['dbNSFP_value_col']), int(md_utilities.hidden_external_tools['LRT']['dbNSFP_pred_col']), ';', 'basic', -1, 'gt', record
                            # )

                            # if external_data['missensePredictions']['lrtPred'] == 'Damaging':
                            #     mpa_missense += 1
                            # if re.search(r'^[DUN]', external_data['missensePredictions']['lrtPred']):
                            #     mpa_avail += 1
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
                                revel = md_utilities.get_value_from_tabix_file('REVEL', md_utilities.local_files['revel']['abs_path'], var, variant_features)
                                if isinstance(revel, str):
                                    external_data['missensePredictions']['revelScore'] = revel
                                else:
                                    external_data['missensePredictions']['revelScore'] = float(revel[int(md_utilities.external_tools['REVEL']['value_col'])])
                                internal_data['missensePredictions']['revelColor'] = "#000000"
                                external_data['missensePredictions']['revelPred'] = 'no prediction'
                                internal_data['missensePredictions']['revelStar'] = ''
                                # build revel pred
                                # if re.search(r'^[\d\.]+$', external_data['missensePredictions']['revelScore']):
                                if isinstance(external_data['missensePredictions']['revelScore'], float):
                                    external_data['missensePredictions']['revelPred'] = md_utilities.build_revel_pred(external_data['missensePredictions']['revelScore'])
                                    internal_data['missensePredictions']['revelColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['revelScore'], 'revel_min', 'revel_max', 'no_effect')
                                # revel replaces fathmm-mkl in mpa score
                                if external_data['missensePredictions']['revelPred'] == 'Damaging':
                                    mpa_missense += 1
                                if external_data['missensePredictions']['revelPred'] != 'no prediction':
                                    mpa_avail += 1
                            # alphamissense
                            alphamissense = md_utilities.get_value_from_tabix_file('AlphaMissense', md_utilities.local_files['alphamissense']['abs_path'], var, variant_features)
                            if isinstance(alphamissense, str):
                                external_data['missensePredictions']['amScore'] = alphamissense
                            else:
                                external_data['missensePredictions']['amScore'] = float(format(float(alphamissense[int(md_utilities.external_tools['AlphaMissense']['value_col'])]), '.3f'))
                            internal_data['missensePredictions']['amColor'] = "#000000"
                            external_data['missensePredictions']['amPred'] = 'no prediction'
                            internal_data['missensePredictions']['amStar'] = ''
                            # build alphamissense pred
                            if isinstance(external_data['missensePredictions']['amScore'], float):
                                external_data['missensePredictions']['amPred'] = md_utilities.predictors_translations['alphamissense'][alphamissense[int(md_utilities.external_tools['AlphaMissense']['pred_col'])]]
                                internal_data['missensePredictions']['amColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['amScore'], 'am_min', 'am_max', 'no_effect')
                            # am replaces lrt in mpa score
                            if external_data['missensePredictions']['amPred'] == 'Damaging':
                                mpa_missense += 1
                            if external_data['missensePredictions']['amPred'] != 'no prediction':
                                mpa_avail += 1
                            # meta SVM
                            external_data['missensePredictions']['metaSVMScore'] = record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_msvm'])]
                            internal_data['missensePredictions']['metaSVMColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['metaSVMScore'], 'meta-svm')
                            external_data['missensePredictions']['metaSVMScore'] = format(float(external_data['missensePredictions']['metaSVMScore']), '.3f')
                            external_data['missensePredictions']['metaSVMPred'] = md_utilities.predictors_translations['basic'][record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_pred_msvm'])]]
                            if external_data['missensePredictions']['metaSVMPred'] == 'Damaging':
                                mpa_missense += 1
                            if external_data['missensePredictions']['metaSVMPred'] != 'no prediction':
                                mpa_avail += 1
                            # meta LR
                            external_data['missensePredictions']['metaLRScore'] = record[int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_mlr'])]
                            internal_data['missensePredictions']['metaLRColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['metaLRScore'], 'meta-lr')
                            external_data['missensePredictions']['metaLRScore'] = format(float(external_data['missensePredictions']['metaLRScore']), '.3f')
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
                        # mistic
                        if variant_features['prot_type'] == 'missense' and \
                                external_data['gene']['chromosome'] != 'Y':
                            record = md_utilities.get_value_from_tabix_file('Mistic', md_utilities.local_files['mistic']['abs_path'], var, variant_features)
                            if isinstance(record, str):
                                external_data['missensePredictions']['misticScore'] = record
                            else:
                                external_data['missensePredictions']['misticScore'] = record[int(md_utilities.external_tools['Mistic']['value_col'])]
                                # external_data['missensePredictions']['misticScore'] = record[4]
                            internal_data['missensePredictions']['misticColor'] = "#000000"
                            external_data['missensePredictions']['misticPred'] = 'no prediction'
                            if re.search(r'^[\d\.]+$', external_data['missensePredictions']['misticScore']):
                                external_data['missensePredictions']['misticScore'] = format(float(external_data['missensePredictions']['misticScore']), '.2f')
                                internal_data['missensePredictions']['misticColor'] = md_utilities.get_preditor_single_threshold_color(external_data['missensePredictions']['misticScore'], 'mistic')
                                external_data['missensePredictions']['misticPred'] = 'Tolerated'
                                if float(external_data['missensePredictions']['misticScore']) > md_utilities.predictor_thresholds['mistic']:
                                    external_data['missensePredictions']['misticPred'] = 'Damaging'
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
                if variant_features['dna_type'] == 'substitution':
                    # promoterAI
                    # if variant_features['start_segment_type'] == '5UTR':
                    if variant_features['c_name'] is None or \
                            re.search(r'^-', variant_features['c_name']):
                        record = md_utilities.get_value_from_tabix_file('PromoterAI', md_utilities.local_files['promoterai']['abs_path'], var, variant_features)
                        if isinstance(record, str):
                            internal_data['noMatch']['promoterai'] = "{0} {1}".format(record, md_utilities.external_tools['PromoterAI']['version'])
                        else:
                            external_data['nonCodingPredictions']['promoterai'] = format(float(record[int(md_utilities.external_tools['PromoterAI']['raw_col'])]), '.2f')
                            internal_data['nonCodingPredictions']['promoteraiColor'] = md_utilities.get_preditor_single_threshold_color(abs(float(external_data['nonCodingPredictions']['promoterai'])), 'promoterai')
                    # GPN-MSA
                    record = md_utilities.get_value_from_tabix_file('GPN-MSA', md_utilities.local_files['gpnmsa']['abs_path'], var, variant_features)
                    if isinstance(record, str):
                        internal_data['noMatch']['gpnmsa'] = "{0} {1}".format(record, md_utilities.external_tools['GPN-MSA']['version'])
                    else:
                        external_data['overallPredictions']['gpnmsa'] = format(float(record[int(md_utilities.external_tools['GPN-MSA']['raw_col'])]), '.2f')
                        internal_data['overallPredictions']['gpnmsaColor'] = md_utilities.get_preditor_single_threshold_reverted_color(float(external_data['overallPredictions']['gpnmsa']), 'gpnmsa')
                    # ReMM
                    if not variant_features['prot_type'] or variant_features['prot_type'] == 'unknown':
                        record = md_utilities.get_value_from_tabix_file('ReMM', md_utilities.local_files['remm']['abs_path'], var, variant_features)
                        if isinstance(record, str):
                            internal_data['noMatch']['remm'] = "{0} {1}".format(record, md_utilities.external_tools['ReMM']['version'])
                        else:
                            external_data['nonCodingPredictions']['remm'] = format(float(record[int(md_utilities.external_tools['ReMM']['raw_col'])]), '.3f')
                            internal_data['nonCodingPredictions']['remmColor'] = md_utilities.get_preditor_double_threshold_color(float(external_data['nonCodingPredictions']['remm']), 'remm_lp', 'remm_p')
                    # Phylop-Pri
                    record = md_utilities.get_bigwig_score('phyloPPrimates', md_utilities.local_files['phylop_primates_bw']['abs_path'], var)
                    if isinstance(record, str):
                        internal_data['noMatch']['phylop_primates'] = "{0} {1}".format(record, md_utilities.external_tools['phyloPPrimates']['version'])                        
                    else:
                        external_data['overallPredictions']['phylop_primates'] = format(float(record), '.3f')
                        internal_data['overallPredictions']['phylop_primatesColor'] = md_utilities.get_preditor_single_threshold_color(float(external_data['overallPredictions']['phylop_primates']), 'phylop_primates')
                    # cactus 241 way
                    record = md_utilities.get_bigwig_score('Cactus_241_way', md_utilities.local_files['cactus241way_bw']['abs_path'], var)
                    if isinstance(record, str):
                        internal_data['noMatch']['cactus241way'] = "{0} {1}".format(record, md_utilities.external_tools['Cactus_241_way']['version'])
                    else:
                        external_data['overallPredictions']['cactus241way'] = format(float(record), '.3f')
                        internal_data['overallPredictions']['cactus241wayColor'] = md_utilities.get_preditor_single_threshold_color(float(external_data['overallPredictions']['cactus241way']), 'cactus241way')
                    if var_type == 'genic':
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
                else:
                    internal_data['noMatch']['gpnmsa'] = "No precomputed score for GPN-MSA {0}".format(md_utilities.external_tools['GPN-MSA']['version'])
                    internal_data['noMatch']['cactus241way'] = "No precomputed score for cactus241way {0}".format(md_utilities.external_tools['Cactus_241_way']['version'])
                    internal_data['noMatch']['phylop_primates'] = "No precomputed score for PhyloP Primates {0}".format(md_utilities.external_tools['phyloPPrimates']['version'])
                    # ReMM indels
                    # ReMM gives scores per positions not per variant
                    # we can return a table of all scores encompassing the del - what could be done for ins?
                    if (variant_features['dna_type'] == 'deletion' or \
                            variant_features['dna_type'] == 'indel') and \
                            (not variant_features['prot_type'] or \
                            variant_features['prot_type'] == 'unknown'):
                        start_del = end_del = external_data['VCF']['hg38']['pos']
                        if variant_features['variant_size'] > 1:
                            start_del, end_del = md_utilities.compute_start_end_pos(external_data['nomenclatures']['hg38gName'])
                        records = md_utilities.get_max_value_from_tabix_region('ReMM', md_utilities.local_files['remm']['abs_path'], external_data['VCF']['chr'], start_del, end_del)
                        if isinstance(records, str):
                            internal_data['noMatch']['remm'] = "{0} {1}".format(record, md_utilities.external_tools['ReMM']['version'])
                        else:
                            # external_data['nonCodingPredictions']['remm'] = records
                            # transform tabix.iter object into list otherwise jinja does not want to iterate on it
                            remm_del = []
                            for record in records:
                                tmp_list = record
                                tmp_list.append(md_utilities.get_preditor_double_threshold_color(record[2], 'remm_lp', 'remm_p'))
                                remm_del.append(tmp_list)
                                # remm_del.append(record)
                                # print(record)
                            external_data['nonCodingPredictions']['remm'] = remm_del
                if var_type == 'genic':
                    # MaveDB
                    record = md_utilities.get_value_from_tabix_file('MaveDB', md_utilities.local_files['mavedb']['abs_path'], var, variant_features)
                    if isinstance(record, str):
                        internal_data['noMatch']['mavedb'] = "{0} {1}".format(record, md_utilities.external_tools['MaveDB']['version'])
                    else:
                        external_data['functionalStudies']['mavedb_score'] = format(float(record[int(md_utilities.external_tools['MaveDB']['score_col'])]), '.2f')
                        external_data['functionalStudies']['mavedb_prot'] = record[int(md_utilities.external_tools['MaveDB']['prot_col'])]
                        external_data['functionalStudies']['mavedb_urn'] = record[int(md_utilities.external_tools['MaveDB']['urn_col'])]
                        external_data['functionalStudies']['mavedb_var_urn'] = record[int(md_utilities.external_tools['MaveDB']['variant_urn_col'])]
                    # spliceAI 1.3
                    # ##INFO=<ID=SpliceAI,Number=.,Type=String,Description="SpliceAIv1.3 variant annotation.
                    # These include delta scores (DS) and delta positions (DP) for acceptor gain (AG), acceptor loss (AL), donor gain (DG), and donor loss (DL).
                    # Format: ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL">
                    spliceai_res = False
                    if variant_features['dna_type'] == 'substitution':
                        record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai_snvs']['abs_path'], var, variant_features, db)
                        spliceai_res = True
                    elif ((variant_features['dna_type'] == 'insertion' and
                            internal_data['positions']['insSize'] == 1) or
                            (variant_features['dna_type'] == 'duplication' and
                            variant_features['variant_size'] == 1) or
                            (variant_features['dna_type'] == 'deletion' and
                                variant_features['variant_size'] <= 4)):
                        record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai_indels']['abs_path'], var, variant_features, db)
                        # print(record)
                        spliceai_res = True
                    if spliceai_res is True:
                        if isinstance(record, str):
                            internal_data['noMatch']['spliceai'] = "{0} {1}".format(record, md_utilities.external_tools['spliceAI']['version'])
                        else:
                            # check if warning coming from spliceai and gene symbol conflict
                            if len(record) == 9:
                                # warning
                                internal_data['spliceai_warning'] = record[8]
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
                                    internal_data['splicingPredictions'][id_color] = md_utilities.get_splice_predictor_color(
                                        'spliceai',
                                        float(external_data['splicingPredictions'][identifier])
                                    )
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
                    # AbSplice
                    # results are stored in a tabix file, on file per gene
                    # so we need to get the file and then the results - 49 tissus, 49 results
                    # SNVs only
                    if external_data['positions']['DNAType'] == 'substitution':
                        absplice_file = '{0}{1}.tsv.gz'.format(
                                    md_utilities.local_files['absplice']['abs_path'],
                                    external_data['gene']['hgncId']
                                )
                        if os.path.isfile(absplice_file):
                            record = md_utilities.get_value_from_tabix_file(
                                'AbSplice',
                                absplice_file,
                                var,
                                variant_features
                            )
                            if isinstance(record, str):
                                # No match in AbSplice v3
                                internal_data['noMatch']['abSplice'] = "< 0.01 in {0}".format(md_utilities.external_tools['AbSplice']['version'])
                            else:
                                internal_data['splicingPredictions']['abSpliceResults'] = True
                                # parse the file header to get:
                                # - AbSplice_DNA_Tissue
                                # - number of tissues vary from each file
                                # - values can be empty?
                                # then add the corresponding predictions
                                # build dict with interesting header and value
                                with gzip.open(absplice_file, 'rt') as f:
                                    headers = f.readline().split('\t')
                                external_data['splicingPredictions']['abSplice'] = dict(zip(headers, record))
                                # get max absplice score
                                # reduce dic with only interesting features?
                                # build 2 lists with only AbSplice_DNA_Tissue and values
                                # and get max absplice score
                                tmp_max = 0
                                tmp_tissue = ''
                                for header in external_data['splicingPredictions']['abSplice']:
                                    if external_data['splicingPredictions']['abSplice'][header] == '':
                                            # do not consider empty values
                                            continue
                                    match_obj = re.search(r'^AbSplice_DNA_(\w+)$', header)
                                    if match_obj:
                                        internal_data['splicingPredictions']['abspliceDNAHeader'].append(match_obj.group(1).replace('_', ' '))
                                        internal_data['splicingPredictions']['abspliceDNAValues'].append(
                                            external_data['splicingPredictions']['abSplice'][header]
                                        )
                                        if ((tmp_max > 0 and 
                                                float(external_data['splicingPredictions']['abSplice'][header]) >  tmp_max) or 
                                                tmp_max == 0):
                                            tmp_max = float(external_data['splicingPredictions']['abSplice'][header])
                                            tmp_tissue = match_obj.group(1).replace('_', ' ')
                                if tmp_max > 0:
                                    internal_data['splicingPredictions']['abSpliceMaxColor'] = md_utilities.get_splice_predictor_color(
                                        'absplice',
                                        tmp_max
                                    )
                                    external_data['splicingPredictions']['abSplice']['maxScore'] = tmp_max
                                    external_data['splicingPredictions']['abSplice']['maxTissue'] = tmp_tissue
                    # MorfeeDB
                    # bgzipped tabixed file
                    # we may have multiple results per position, sep ';'
                    if re.search(r'^c\.-.+', external_data['nomenclatures']['cName']) and \
                            external_data['positions']['segmentStartType'] == 'exon' and \
                            external_data['positions']['DNAType'] == 'substitution':
                        morfee_vf = variant_features
                        morfee_vf['enst'] = external_data['gene']['ENST']
                        record = md_utilities.get_value_from_tabix_file(
                            'MorfeeDB',
                            md_utilities.local_files['morfeedb']['abs_path'],
                            var,
                            morfee_vf
                        )
                        if isinstance(record, str):
                            # No match in AbSplice v3
                            internal_data['noMatch']['morfeedb'] = record
                        else:
                            # create gtf file to be displayed in igv.js
                            gtf_file_basename = '{0}{1}.gtf'.format(
                                md_utilities.local_files['morfeedb_folder']['abs_path'],
                                variant_id
                            )
                            with open(
                                gtf_file_basename,
                                'w'
                            ) as gtf_file:
                                i = 0
                                for morfee_entry in record:
                                    if i > 0:
                                        external_data['morfeedb'].append({
                                            'orfSNVs_type': None,
                                            'orfSNVs_frame': None,
                                            'type_of_generated_ORF': None,
                                            'Ratio_length_pred_obs': None,
                                            'TIS_sequence': None,
                                            'STOP_sequence': None,
                                            'Kozak_sequence': None,
                                            'Kozak_score': None,
                                            'Kozak_strength': None,
                                            'TIS_c_pos': None,
                                            'STOP_c_pos': None,
                                        })
                                    for morfee_type in external_data['morfeedb'][i]:
                                        # get values - and for some reducs the number of decimals
                                        # print(morfee_type)
                                        if morfee_type == 'Ratio_length_pred_obs':
                                            external_data['morfeedb'][i][morfee_type] = format(float(morfee_entry[int(md_utilities.external_tools['MorfeeDB'][morfee_type])]), '.4f')
                                        elif morfee_type == 'Kozak_score':
                                            kozak_str = ''
                                            kozaks = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB'][morfee_type])].replace(' ', ''))
                                            for kozak in kozaks:
                                                if kozak == 'NA' or \
                                                        kozak == 'na':
                                                    kozak_str = '{0}{1}; '.format(kozak_str, kozak)
                                                else:
                                                    kozak_str = '{0}{1}; '.format(kozak_str, format(float(kozak), '.2f'))
                                            # we remove trailing ;
                                            final_kozak_str = kozak_str[:-2]
                                            external_data['morfeedb'][i][morfee_type] = final_kozak_str
                                        else:
                                            external_data['morfeedb'][i][morfee_type] = morfee_entry[int(md_utilities.external_tools['MorfeeDB'][morfee_type])]
                                    orf_pos_dict = dict(
                                        zip(
                                            re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['TIS_position'])].replace(' ', '')),
                                            re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['STOP_position'])].replace(' ', '')), 
                                        )
                                    )
                                    j = 0
                                    # build tables for multiple results for the gtf file
                                    orfSNVs_frames = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['orfSNVs_frame'])].replace(' ', ''))
                                    type_of_generated_ORFs = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['type_of_generated_ORF'])].replace(' ', ''))
                                    TIS_c_poss = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['TIS_c_pos'])].replace(' ', ''))
                                    STOP_c_poss = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['STOP_c_pos'])].replace(' ', ''))
                                    Kozak_scores = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['Kozak_score'])].replace(' ', ''))
                                    Kozak_strengths = re.split(';', morfee_entry[int(md_utilities.external_tools['MorfeeDB']['Kozak_strength'])].replace(' ', ''))
                                    # print(TIS_c_poss)
                                    for start_pos in orf_pos_dict:
                                        start, end = start_pos, int(orf_pos_dict[start_pos])
                                        if external_data['gene']['strand'] == '-':
                                            start, end = int(orf_pos_dict[start_pos]), start_pos
                                        # bed_file.write('{0}\t{1}\t{2}\n'.format(external_data['VCF']['chr'], start-1, end
                                        # gtf format https://www.ensembl.org/info/website/upload/gff.html?redirect=no
                                        gtf_file.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}\n'.format(
                                            external_data['VCF']['chr'],
                                            'MORFEE',
                                            morfee_entry[int(md_utilities.external_tools['MorfeeDB']['orfSNVs_type'])],
                                            start,
                                            end,
                                            '.',
                                            external_data['gene']['strand'],
                                            '.',
                                            'orfSNVs_type {0};orfSNVs_frame {1};type_of_generated_ORF {2};Ratio_length_pred_obs {3};TIS_c_pos {4};STOP_c_pos {5};Kozak_score {6};Kozak_strength {7}'.format(
                                                morfee_entry[int(md_utilities.external_tools['MorfeeDB']['orfSNVs_type'])],
                                                orfSNVs_frames[j],
                                                type_of_generated_ORFs[j],
                                                morfee_entry[int(md_utilities.external_tools['MorfeeDB']['Ratio_length_pred_obs'])],
                                                TIS_c_poss[j],
                                                STOP_c_poss[j],
                                                Kozak_scores[j] if j < len(Kozak_scores) else 'NA',
                                                Kozak_strengths[j] if j < len(Kozak_scores) else 'NA'
                                            )
                                        ))
                                        j += 1
                                    i += 1
                        # print(external_data['morfeedb'])
        for var in variant:
            # 2nd loop as we need to fetch hg38 first, to get revel scores
            if var['genome_version'] == 'hg19':
                # ncbi chr
                curs.execute(
                    """
                    SELECT ncbi_name
                    FROM chromosomes
                    WHERE name = %s
                    AND genome_version = %s
                    """,
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
                if var_type == 'genic':
                    # if no REVEL score in hg38 (REVEL hg38 were obtained by liftover, https://sites.google.com/site/revelgenomics/downloads)
                    # then try to retrieve in hg19
                    if academic is True:
                        if not isinstance(external_data['missensePredictions']['revelScore'], float):
                            revel = md_utilities.get_value_from_tabix_file('REVEL', md_utilities.local_files['revel_hg19']['abs_path'], var, variant_features)
                            if isinstance(revel, str):
                                external_data['missensePredictions']['revelScore'] = revel
                            else:
                                external_data['missensePredictions']['revelScore'] = revel[int(md_utilities.external_tools['REVEL']['value_col'])]
                            internal_data['missensePredictions']['revelColor'] = "#000000"
                            external_data['missensePredictions']['revelPred'] = 'no prediction'
                            # build revel pred
                            if re.search(r'^[\d\.]+$', external_data['missensePredictions']['revelScore']):
                                external_data['missensePredictions']['revelPred'] = md_utilities.build_revel_pred(external_data['missensePredictions']['revelScore'])
                                internal_data['missensePredictions']['revelColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['revelScore'], 'revel_min', 'revel_max')
                                internal_data['missensePredictions']['revelStar'] = '**'
                    # if no alphamissense in hg38, try to find a score in the hg19 dataset
                    if not isinstance(external_data['missensePredictions']['amScore'], float):
                        alphamissense = md_utilities.get_value_from_tabix_file('AlphaMissense', md_utilities.local_files['alphamissense_hg19']['abs_path'], var, variant_features)
                        if isinstance(alphamissense, str):
                            external_data['missensePredictions']['amScore'] = alphamissense
                        else:
                            external_data['missensePredictions']['amScore'] = float(format(float(alphamissense[int(md_utilities.external_tools['AlphaMissense']['value_col'])]), '.3f'))
                        internal_data['missensePredictions']['amColor'] = "#000000"
                        external_data['missensePredictions']['amPred'] = 'no prediction'
                        # build alphamissense pred
                        if isinstance(external_data['missensePredictions']['amScore'], float):
                            external_data['missensePredictions']['amPred'] = md_utilities.predictors_translations['alphamissense_hg19'][alphamissense[int(md_utilities.external_tools['AlphaMissense']['pred_col'])]]
                            internal_data['missensePredictions']['amColor'] = md_utilities.get_preditor_double_threshold_color(external_data['missensePredictions']['amScore'], 'am_min', 'am_max', 'no_effect')
                            internal_data['missensePredictions']['amStar'] = '**'
        if var_type == 'genic':
            internal_data['splicingPredictions']['splicingRadarLabels'] = splicing_radar_labels
            internal_data['splicingPredictions']['splicingRadarValues'] = splicing_radar_values
        # get classification info
        id_list = [variant_id]
        if other_ids:
            for id in other_ids:
                id_list.append(id)
        id_tuple = tuple(id_list)
        curs.execute(
            """
            SELECT a.variant_feature_id, a.acmg_class, a.class_date,
            a.comment, b.id, b.email, b.email_pref, b.username,
            c.html_code, c.acmg_translation, d.c_name, d.gene_symbol, d.refseq
            FROM class_history a, mobiuser b, valid_class c, variant_feature d
            WHERE a.mobiuser_id = b.id
                AND a.acmg_class = c.acmg_class
                AND a.variant_feature_id = d.id
                AND a.variant_feature_id IN %s
            ORDER BY a.class_date ASC
            """,
            [id_tuple]
        )
        class_history = curs.fetchall()
        if len(class_history) == 0:
            class_history = None
        if var_type == 'genic':
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
            # spip_cache = 0
            result_spip = ''
            if os.path.exists(
                    '{0}{1}.txt'.format(md_utilities.local_files['spip']['abs_path'], external_data['variantId'])
                    ):
                with open(r'{0}{1}.txt'.format(md_utilities.local_files['spip']['abs_path'], external_data['variantId'])) as spip_file:
                    num_lines = len(spip_file.readlines())
                if num_lines == 2:
                    with open('{0}{1}.txt'.format(md_utilities.local_files['spip']['abs_path'], external_data['variantId']), "r") as spip_out:
                        result_spip = spip_out.read()
            if not result_spip:
                result_spip = md_utilities.run_spip(
                    external_data['gene']['symbol'],
                    external_data['gene']['RefSeqTranscript'],
                    internal_data['nomenclatures']['cName'],
                    external_data['variantId']
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
            favourite=favourite,
            urls=md_utilities.urls,
            external_tools=md_utilities.external_tools,
            thresholds=md_utilities.predictor_thresholds,
            class_history=class_history,
            external_data=external_data,
            internal_data=internal_data
        )


# -------------------------------------------------------------------
# api - variant create


@bp.route('/api/variant/create', methods=['GET', 'POST'])
def api_variant_create(variant_chgvs=None, caller='browser', api_key=None):
    # check and get params
    match_variant_chgvs = None
    if md_utilities.get_post_param(request, 'caller'):
        caller = 'cli' if md_utilities.get_post_param(request, 'caller') == 'cli' else 'browser'
    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.')
        else:
            return redirect(url_for('md.index'), code=302)
    variant_regexp = md_utilities.regexp['variant']
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    if md_utilities.get_post_param(request, 'variant_chgvs'):
        match_variant_chgvs = re.search(
            rf'^({ncbi_transcript_regexp}:c\.{variant_regexp})',
            urllib.parse.unquote(md_utilities.get_post_param(request, 'variant_chgvs'))
        )
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if not g.user:
        # external API call - or non-connected user on webUI
        # res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_post_param(request, 'api_key'))
        res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_api_key_from_request(request))
        if 'mobidetails_error' in res_check_api_key:
            close_db()
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']
    header = md_utilities.api_agent
    # code for when vv will require a token
    # vv_header = urllib3.make_headers(
    #     basic_auth='{0}:'.format(md_utilities.get_vv_token()),
    #     user_agent=md_utilities.user_agent
    # )
    # basic_auth='{0}:'.format(md_utilities.get_vv_token()),
    if caller and \
            match_variant_chgvs:
        variant_chgvs = match_variant_chgvs.group(1)
        match_object = re.search(
            rf'^({ncbi_transcript_regexp}):c\.({variant_regexp})',
            variant_chgvs
        )
        if match_object:
            acc_no, new_variant = match_object.group(1), match_object.group(2)
            new_variant = new_variant.replace(" ", "").replace("\t", "")
            original_variant = new_variant
            curs.execute(
                """
                SELECT id
                FROM variant_feature
                WHERE c_name = %s
                    AND refseq = %s
                """,
                (new_variant, acc_no)
            )
            res = curs.fetchone()
            if res is not None:
                close_db()
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
                    """
                    SELECT gene_symbol, canonical
                    FROM gene
                    WHERE refseq = %s
                        AND variant_creation IN ('ok', 'hg19_mapping_default')
                    """,
                    (acc_no,)
                )
                res_gene = curs.fetchone()
                if not res_gene:
                    # decompose transcript and check if it's a version pb
                    refseq, submitted_version = acc_no.split(".")
                    curs.execute(
                        """
                        SELECT refseq
                        FROM gene
                        WHERE refseq LIKE %s
                            AND variant_creation IN ('ok', 'hg19_mapping_default')
                        """,
                        ('{0}%'.format(refseq),)
                    )
                    res_version = curs.fetchall()
                    if res_version:
                        close_db()
                        if caller == 'cli':
                            return jsonify(
                                mobidetails_error="It seems that your transcript version ({0}) does not match MobiDetails ({1}).".format(
                                    acc_no, ','.join(version['refseq'] for version in res_version)
                                )
                            )
                        else:
                            flash(
                                """
                                It seems that your transcript version ({0}) does not match MobiDetails ({1}).
                                """.format(acc_no, ','.join(version['refseq'] for version in res_version)),
                                'w3-pale-red'
                            )
                            return redirect(url_for('md.index'), code=302)
                    if caller == 'cli':
                        close_db()
                        return jsonify(
                            mobidetails_error="The transcript corresponding to {} is not  available for variant annotation in MobiDetails.".format(acc_no)
                        )
                    else:
                        flash(
                            """
                            The gene corresponding to {} is not available for variant annotation in MobiDetails.
                            """.format(acc_no),
                            'w3-pale-red'
                        )
                        return redirect(url_for('md.index'), code=302)

                vv_base_url = md_utilities.get_vv_api_url(caller)
                # print(vv_base_url)
                if not vv_base_url:
                    close_db()
                    if caller == 'cli':
                        return jsonify(mobidetails_error='Variant Validator looks down!')
                    else:
                        flash('Variant Validator looks down!', 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
                vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}:c.{2}/all?content-type=application/json".format(
                    vv_base_url, acc_no, new_variant
                )
                vv_key_var = "{0}:c.{1}".format(acc_no, new_variant)
                try:
                    vv_data = json.loads(
                        http.request(
                            'GET',
                            vv_url,
                        ).data.decode('utf-8')
                    )
                    # print(vv_header)
                    # print(vv_url)
                except Exception:
                    close_db()
                    if caller == 'cli':
                        return jsonify(
                            mobidetails_error="Variant Validator did not return any value for the variant {}.".format(new_variant)
                        )
                    else:
                        try:
                            flash(
                                """
                                There has been an issue with the annotation of the variant via VariantValidator.
                                The error is the following: {}
                                """.format(vv_data['validation_warning_1']['validation_warnings']),
                                'w3-pale-red'
                            )
                        except Exception:
                            flash(
                                """There has been an issue with the annotation of the variant via VariantValidator (likely a timeout).
                                Sorry for the inconvenience. You may want to try again in a few minutes.
                                """,
                                'w3-pale-red'
                            )
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
                        return redirect(url_for('md.index'), code=302)
                vv_error = md_utilities.vv_internal_server_error(caller, vv_data, vv_key_var)
                if vv_error != 'vv_ok':
                    close_db()
                    if caller == 'cli':
                        return jsonify(vv_error)
                    else:
                        flash(vv_error)
                        return redirect(url_for('md.index'), code=302)
                vv_variant_data_check = md_utilities.check_vv_variant_data(vv_key_var, vv_data)
                # if md_utilities.check_vv_variant_data(vv_key_var, vv_data) is not True:
                if vv_variant_data_check is not True:
                    close_db()
                    if caller == 'browser':
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
                            flash(
                                """
                                VariantValidator did not return a valid value for the variant {0} {1}. An admin has been warned.
                                """.format(vv_key_var, vv_variant_data_check),
                                'w3-pale-red'
                            )
                        else:
                            flash(
                                """
                                VariantValidator did not return a valid value for the variant {0}: {1} {2}
                                """.format(vv_key_var, vv_warning, vv_variant_data_check),
                                'w3-pale-red'
                            )
                        return redirect(url_for('md.index'), code=302)
                    elif caller == 'cli':
                        return jsonify(
                            mobidetails_error=
                            "VariantValidator did not return a valid value for the variant {0} {1}".format(vv_key_var, vv_variant_data_check)
                        )
                # if re.search('[di][neu][psl]', new_variant):
                    # need to redefine vv_key_var for indels as the variant name returned
                    # by vv is likely to be different form the user's
                for key in vv_data.keys():
                    if re.search(acc_no, key):
                        vv_key_var = key
                        # print(key)
                        var_obj = re.search(r':c\.(.+)$', key)
                        if var_obj is not None:
                            new_variant = var_obj.group(1)
                # check if the transcript is canonical - if not, send 2 requests, one for the canonical, the other for the asked trancript
                # returns only the results for the asked transcript (retrocompatibility)
                if res_gene['canonical'] is False:
                    curs.execute(
                        """
                        SELECT refseq
                        FROM gene
                        WHERE gene_symbol = %s
                        AND canonical = 't'
                        """,
                        (res_gene['gene_symbol'],)
                    )
                    res_can = curs.fetchone()
                    # get variant name for this transcript
                    # need another call to VV
                    if vv_data[vv_key_var]['primary_assembly_loci']['grch38']['hgvs_genomic_description']:
                        # special code for vv
                        # vv_special = ''
                        # # vv_provider = md_utilities.urls['rest_vv_genuine']
                        # vv_provider = md_utilities.urls['rest_vv_browser']['3']
                        # # vv_provider = md_utilities.urls['rest_vv']['2']
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
                            vv_data[vv_key_var]['primary_assembly_loci']['grch38']['hgvs_genomic_description'],
                        )
                        try:
                            vv_full_data = json.loads(
                                http.request(
                                    'GET',
                                    vv_url,
                                    headers=header
                                ).data.decode('utf-8')
                            )
                            vv_key_var_can = None
                            for key in vv_full_data.keys():
                                if re.search(res_can['refseq'], key):
                                    vv_key_var_can = key
                                    var_obj = re.search(r':c\.(.+)$', key)
                                    if var_obj is not None:
                                        new_variant_can = var_obj.group(1)
                                        original_variant_can = new_variant_can
                            if vv_key_var_can:
                                md_utilities.create_var_vv(
                                    vv_key_var_can, res_gene['gene_symbol'], res_can['refseq'],
                                    'c.{}'.format(new_variant_can), original_variant_can,
                                    vv_full_data, caller, db, g
                                )
                        except json.decoder.JSONDecodeError:
                            # empty JSON, move on
                            pass
                creation_dict = md_utilities.create_var_vv(
                    vv_key_var, res_gene['gene_symbol'], acc_no,
                    'c.{}'.format(new_variant), original_variant,
                    vv_data, caller, db, g
                )
                close_db()
                if isinstance(creation_dict, int):
                    # success
                    if caller == 'cli':
                        return jsonify(
                            mobidetails_id=creation_dict,
                            url='{0}{1}'.format(
                                request.host_url[:-1],
                                url_for('api.variant', variant_id=creation_dict, caller='browser')
                            )
                        )
                    else:
                        return redirect(url_for('api.variant', variant_id=creation_dict, caller='browser'), code=302)
                elif isinstance(creation_dict, str):
                    if caller == 'cli':
                        return jsonify(mobidetails_error=creation_dict)
                    else:
                        flash(creation_dict, '')
                        return redirect(url_for('md.index'), code=302)
                if 'mobidetails_error' in creation_dict:
                    if caller == 'cli':
                        return jsonify(creation_dict)
                    else:
                        flash(creation_dict['mobidetails_error'], 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
        else:
            close_db()
            if caller == 'cli':
                return jsonify(mobidetails_error='Malformed query {}'.format(urllib.parse.unquote(variant_chgvs)))
            else:
                flash('The query seems to be malformed: {}.'.format(urllib.parse.unquote(variant_chgvs)), 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
    else:
        close_db()
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameters')
        else:
            flash('The submitted parameters looks invalid!!!', 'w3-pale-red')
            return redirect(url_for('md.index'), code=302)

# -------------------------------------------------------------------
# api - variant create from genomic HGVS eg NC_000001.11:g.40817273T>G and gene name (HGNC)


# @bp.route('/api/variant/create_g/<string:variant_ghgvs>/<string:gene>/<string:caller>/<string:api_key>', methods=['GET', 'POST'])
# def api_variant_g_create(variant_ghgvs=None, gene=None, caller=None, api_key=None):
@bp.route('/api/variant/create_g', methods=['GET', 'POST'])
def api_variant_g_create(variant_ghgvs=None, gene_hgnc=None, caller='browser', api_key=None):
    # get params
    match_variant_ghgvs = match_gene_hgnc = None
    # treat params one by one
    if md_utilities.get_post_param(request, 'caller'):
        caller = 'cli' if md_utilities.get_post_param(request, 'caller') == 'cli' else 'browser'
    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.')
        else:
            return redirect(url_for('md.index'), code=302)
    variant_regexp = md_utilities.regexp['variant']
    chrom_regexp = md_utilities.regexp['ncbi_chrom']    
    if md_utilities.get_post_param(request, 'variant_ghgvs'):
        match_variant_ghgvs = re.search(rf'^({chrom_regexp}:g\.{variant_regexp})$', urllib.parse.unquote(md_utilities.get_post_param(request, 'variant_ghgvs')))
    gene_symbol_regexp = md_utilities.regexp['gene_symbol']
    if md_utilities.get_post_param(request, 'gene_hgnc'):
        match_gene_hgnc = re.search(rf'^({gene_symbol_regexp}|\d+)$', urllib.parse.unquote(md_utilities.get_post_param(request, 'gene_hgnc')))

    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if not g.user:
        # external API call - or non-connected user on webUI
        # res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_post_param(request, 'api_key'))
        res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_api_key_from_request(request))
        if 'mobidetails_error' in res_check_api_key:
            close_db()
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']

    header = md_utilities.api_agent

    if caller and \
            match_variant_ghgvs and \
            match_gene_hgnc:
        variant_ghgvs = match_variant_ghgvs.group(1)
        gene_hgnc = match_gene_hgnc.group(1)
        # check if gene exists
        if re.search(r'^\d+$', gene_hgnc):
            # HGNC id submitted
            curs.execute(
                """
                SELECT gene_symbol, refseq
                FROM gene
                WHERE hgnc_id = %s
                    AND canonical = 't'
                    AND variant_creation IN ('ok', 'hg19_mapping_default')
                """,
                (gene_hgnc,)
            )
        else:
            # search for gene symbol
            curs.execute(
                """
                SELECT gene_symbol, refseq
                FROM gene
                WHERE gene_symbol = %s
                    AND canonical = 't'
                    AND variant_creation IN ('ok', 'hg19_mapping_default')
                """,
                (gene_hgnc,)
            )
        res_gene = curs.fetchone()
        if res_gene:
            gene_hgnc = res_gene['gene_symbol']
            match_object = re.search(rf'^({chrom_regexp}):g\.({variant_regexp})', variant_ghgvs)
            if match_object:
                ncbi_chr, g_var = match_object.group(1), match_object.group(2)
                # 1st check hg38
                curs.execute(
                    """
                    SELECT *
                    FROM chromosomes
                    WHERE ncbi_name = %s
                    """,
                    (ncbi_chr,)
                )
                res = curs.fetchone()
                if res:
                    genome_version, chrom = res['genome_version'], res['name']
                    # check if variant exists
                    # must already exist on canonical to be returned
                    curs.execute(
                        """
                        SELECT b.feature_id
                        FROM variant_feature a, variant b, gene c
                        WHERE a.id = b.feature_id
                            AND a.gene_symbol = c.gene_symbol
                            AND a.refseq = c.refseq
                            AND a.gene_symbol = %s
                            AND b.genome_version = %s
                            AND b.g_name = %s
                            AND b.chr = %s
                            AND c.canonical = 't'
                        """,
                        (gene_hgnc, genome_version, g_var, chrom)
                    )
                    res = curs.fetchone()
                    if res:
                        close_db()
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
                        vv_base_url = md_utilities.get_vv_api_url(caller)
                        # print(vv_base_url)
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
                        # special code for vv
                        # vv_special = ''
                        # # # vv_provider = md_utilities.urls['rest_vv_genuine']
                        # vv_provider = md_utilities.urls['rest_vv_browser']['3']
                        # if re.match(rf'{vv_provider}', vv_base_url):
                        #     vv_special = 'auth_'
                        # vv_url = "{0}VariantValidator/variantvalidator/{1}/{2}:g.{3}/{4}all?content-type=application/json".format(
                        #     vv_base_url, genome_vv, ncbi_chr, g_var, vv_special
                        # )
                        # restvv 2025 - comment all above
                        vv_url = "{0}VariantValidator/variantvalidator/{1}/{2}:g.{3}/auth_all?content-type=application/json".format(
                            vv_base_url, genome_vv, ncbi_chr, g_var
                        )
                        # vv_key_var = "{0}.{1}:c.{2}".format(acc_no, acc_version, new_variant)
                        # http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
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
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Variant Validator did not return any value for the variant {}.'.format(urllib.parse.unquote(variant_ghgvs)))
                            else:
                                try:
                                    flash(
                                        """
                                        There has been an issue with the annotation of the variant via VariantValidator.
                                        The error is the following: {}
                                        """.format(vv_data['validation_warning_1']['validation_warnings']),
                                        'w3-pale-red'
                                    )
                                except Exception:
                                    flash(
                                        """
                                        There has been an issue with the annotation of the variant via VariantValidator.
                                        Sorry for the inconvenience. You may want to try again in a few minutes.
                                        """,
                                        'w3-pale-red'
                                    )
                                return redirect(url_for('md.index'), code=302)
                        vv_error = md_utilities.vv_internal_server_error(caller, vv_data, variant_ghgvs)
                        if vv_error != 'vv_ok':
                            close_db()
                            if caller == 'cli':
                                return jsonify(vv_error)
                            else:
                                flash(vv_error)
                                return redirect(url_for('md.index'), code=302)
                        # look for gene acc #
                        # print(vv_data)
                        new_variant = None
                        vv_key_var = None
                        res_gene_non_can_list = []
                        # we still need a list of non canonical NM for the gene of interest
                        curs.execute(
                            """
                            SELECT refseq
                            FROM gene
                            WHERE gene_symbol = %s
                                AND canonical = 'f'
                            """,
                            (gene_hgnc,)
                        )
                        res_gene_non_can = curs.fetchall()
                        gene_symbol = gene_hgnc
                        nm_transcript = res_gene['refseq']
                        for transcript in res_gene_non_can:
                            res_gene_non_can_list.append(transcript['refseq'])
                        for key in vv_data.keys():
                            variant_regexp = md_utilities.regexp['variant']
                            ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
                            match_obj = re.search(rf'^({ncbi_transcript_regexp}):c\.({variant_regexp})', key)
                            if match_obj:
                                vv_refseq = match_obj.group(1)
                                vv_variant = match_obj.group(2)
                                if vv_refseq == res_gene['refseq']:
                                    # treat canonical as priority
                                    new_variant = vv_variant
                                    nm_transcript = res_gene['refseq']
                                    gene_symbol = gene_hgnc
                                    vv_key_var = "{0}:c.{1}".format(vv_refseq, vv_variant)
                                    break
                                elif not vv_key_var:
                                    # take into account non canonical isoforms
                                    # print('{0}:c.{1}'.format(match_obj.group(1), match_obj.group(2)))
                                    if vv_refseq in res_gene_non_can_list:
                                        # check gene in case it is different from the asked one
                                        curs.execute(
                                            """
                                            SELECT gene_symbol
                                            FROM gene
                                            WHERE refseq = %s
                                            """,
                                            (vv_refseq,)
                                        )
                                        res_symbol = curs.fetchone()
                                        if res_symbol:
                                            new_variant = vv_variant
                                            nm_transcript = vv_refseq
                                            gene_symbol = res_symbol['gene_symbol']
                                            vv_key_var = "{0}:c.{1}".format(vv_refseq, vv_variant)
                        if vv_key_var:
                            creation_dict = md_utilities.create_var_vv(
                                vv_key_var, gene_symbol, nm_transcript,
                                'c.{}'.format(new_variant), new_variant,
                                vv_data, caller, db, g
                            )
                            close_db()
                            if isinstance(creation_dict, int):
                                # success
                                if caller == 'cli':
                                    return jsonify(
                                        mobidetails_id=creation_dict,
                                        url='{0}{1}'.format(
                                            request.host_url[:-1],
                                            url_for('api.variant', variant_id=creation_dict, caller='browser')
                                        )
                                    )
                                else:
                                    return redirect(url_for('api.variant', variant_id=creation_dict, caller='browser'), code=302)
                            elif isinstance(creation_dict, str):
                                if caller == 'cli':
                                    return jsonify(mobidetails_error=creation_dict)
                                else:
                                    flash(creation_dict, '')
                                    return redirect(url_for('md.index'), code=302)
                            if 'mobidetails_error' in creation_dict:
                                if caller == 'cli':
                                    return jsonify(creation_dict)
                                else:
                                    flash(creation_dict['mobidetails_error'], 'w3-pale-red')
                                    return redirect(url_for('md.index'), code=302)
                        else:
                            close_db()
                            if caller == 'cli':
                                return jsonify(mobidetails_error='Could not create variant {} (possibly considered as intergenic or mapping on non-coding transcripts only, or simply the VariantValidator API is full - you may want to try again later).'.format(urllib.parse.unquote(variant_ghgvs)), variant_validator_output=vv_data)
                            else:
                                try:
                                    flash(
                                        """
                                        There has been an issue with the annotation of the variant via VariantValidator.
                                        The error is the following: {}
                                        """.format(vv_data['validation_warning_1']['validation_warnings']),
                                        'w3-pale-red'
                                    )
                                except Exception:
                                    flash(
                                        """
                                        This variant may not map on a coding transcript. Currently, Mobidetails does not handle variants on non-coding transcripts. Sorry for the inconvenience.
                                        """,
                                        'w3-pale-red'
                                    )
                                return redirect(url_for('md.index'), code=302)
                else:
                    close_db()
                    if caller == 'cli':
                        return jsonify(mobidetails_error='Unknown chromosome {} submitted or bad genome version (hg38 only)'.format(ncbi_chr))
                    else:
                        flash('The submitted chromosome or genome version looks corrupted (hg38 only).', 'w3-pale-red')
                        return redirect(url_for('md.index'), code=302)
            else:
                close_db()
                if caller == 'cli':
                    return jsonify(mobidetails_error='Malformed query {}'.format(urllib.parse.unquote(variant_ghgvs)))
                else:
                    flash('The query seems to be malformed: {}.'.format(urllib.parse.unquote(variant_ghgvs)), 'w3-pale-red')
                    return redirect(url_for('md.index'), code=302)
        else:
            close_db()
            if caller == 'cli':
                return jsonify(mobidetails_error='The submitted gene is currently not available for variant annotation in MobiDetails')
            else:
                flash(
                    """
                    The gene {} is currently not available for variant annotation in MobiDetails
                    """.format(gene_hgnc),
                    'w3-pale-red'
                )
                return redirect(url_for('md.index'), code=302)
    else:
        close_db()
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameters')
        else:
            flash('The submitted parameters looks invalid!!!', 'w3-pale-red')
            return redirect(url_for('md.index'), code=302)
# -------------------------------------------------------------------
# api - variant create from NCBI dbSNP rs id


@bp.route('/api/variant/create_rs', methods=['GET', 'POST'])
def api_variant_create_rs(rs_id=None, caller='browser', api_key=None):
    # check and get params
    match_rs_id = None
    if md_utilities.get_post_param(request, 'caller'):
        caller = 'cli' if md_utilities.get_post_param(request, 'caller') == 'cli' else 'browser'
    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.')
        else:
            return redirect(url_for('md.index'), code=302)
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if not g.user:
        # external API call - or non-connected user on webUI
        # res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_post_param(request, 'api_key'))
        res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_api_key_from_request(request))
        if 'mobidetails_error' in res_check_api_key:
            close_db()
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']
    if md_utilities.get_post_param(request, 'rs_id'):
        match_rs_id = re.search(r'^rs(\d+)$', urllib.parse.unquote(md_utilities.get_post_param(request, 'rs_id')))
    header = md_utilities.api_agent
    if caller and \
            match_rs_id:
        rs_id = 'rs{}'.format(match_rs_id.group(1))
        # check rs_id
        trunc_rs_id = match_rs_id.group(1)
        if trunc_rs_id:
            # check if rsid exists
            curs.execute(
                """
                SELECT c_name, id, refseq
                FROM variant_feature
                WHERE dbsnp_id = %s
                """,
                (trunc_rs_id,)
            )
            res_rs = curs.fetchall()
            if res_rs:
                vars_rs = {}
                for var in res_rs:
                    current_var = '{0}:c.{1}'.format(var['refseq'], var['c_name'])
                    vars_rs[current_var] = {
                        'mobidetails_id': var['id'],
                        'url': '{0}{1}'.format(
                            request.host_url[:-1],
                            url_for('api.variant', variant_id=var['id'], caller='browser')
                        )
                    }
                close_db()
                if caller == 'cli':
                    return jsonify(vars_rs)
                else:
                    if len(res_rs) == 1:
                        for var in res_rs:
                            return redirect(url_for('api.variant', variant_id=var['id'], caller='browser'), code=302)
                    else:
                        return render_template('md/variant_multiple.html', vars_rs=vars_rs)
            # use NCBI API to get HGVS nomenclatures
            ncbi_api_url = "{0}{1}".format(
                md_utilities.urls['ncbi_snp_api'], trunc_rs_id
            )
            try:
                ncbi_api_data = json.loads(
                    http.request(
                        'GET',
                        ncbi_api_url,
                        headers=header
                    ).data.decode('utf-8')
                )
            except Exception:
                close_db()
                if caller == 'cli':
                    return jsonify(mobidetails_error='The NCBI API did not return any value for the variant rs{}.'.format(trunc_rs_id))
                else:
                    flash(
                        """
                        'The NCBI API did not return any value for the variant rs{}
                        """.format(trunc_rs_id),
                        'w3-pale-red'
                    )
                    return redirect(url_for('md.index'), code=302)
            md_response = {}
            hgvs_nc = []
            gene_symbols = []
            # can_nm = None
            if 'error' in ncbi_api_data:
                close_db()
                if caller == 'cli':
                    return jsonify(mobidetails_error='The NCBI API returned an error for the variant rs{0}: {1}'.format(trunc_rs_id, ncbi_api_data['error']['message']))
                else:
                    flash(
                        """
                        'The NCBI API returned an error for the variant rs{0}: {1}
                        """.format(trunc_rs_id, ncbi_api_data['error']['message']),
                        'w3-pale-red'
                    )
                    return redirect(url_for('md.index'), code=302)
            if 'primary_snapshot_data' in ncbi_api_data and \
                    'placements_with_allele' in ncbi_api_data['primary_snapshot_data']:
                for seq_details in ncbi_api_data['primary_snapshot_data']['placements_with_allele']:
                    if 'alleles' in seq_details:
                        for seq_details2 in seq_details['alleles']:
                            if 'hgvs' in seq_details2 and \
                                    not re.search(r'=', seq_details2['hgvs']):
                                hgvs = seq_details2['hgvs']
                                # works for exonic variants because mutalyzer returns no NM for intronic variants
                                variant_regexp = md_utilities.regexp['variant']
                                ncbi_chrom_regexp = md_utilities.regexp['ncbi_chrom']
                                # intronic variant?
                                # we need HGVS genomic to launch the API but also the gene - got from NG
                                # f-strings usage https://stackoverflow.com/questions/6930982/how-to-use-a-variable-inside-a-regular-expression
                                # https://www.python.org/dev/peps/pep-0498/
                                match_nc = re.search(rf'^({ncbi_chrom_regexp}):g\.({variant_regexp})$', hgvs)
                                if match_nc:
                                    # if hg38, we keep it in a variable that can be useful later
                                    curs.execute(
                                        """
                                        SELECT name, genome_version
                                        FROM chromosomes
                                        WHERE ncbi_name = %s
                                        """,
                                        (match_nc.group(1),)
                                    )
                                    res_chr = curs.fetchone()
                                    if res_chr and \
                                            res_chr['genome_version'] == 'hg38':
                                        hgvs_nc.append(hgvs)
                                        # look for gene symbol
                                        positions = md_utilities.compute_start_end_pos(match_nc.group(2))
                                        if not gene_symbols:
                                            # we want gene symbols spanning the genomic position
                                            # we need to hit mygene.info with shtg like:
                                            # https://mygene.info/v3/query?q=chr1%3A216524862-216524862&fields=symbol&species=human
                                            # to get
                                            # {
                                            #   "took": 21,
                                            #   "total": 1,
                                            #   "max_score": 8.792146,
                                            #   "hits": [
                                            #     {
                                            #       "_id": "2104",
                                            #       "_score": 8.792146,
                                            #       "symbol": "ESRRG"
                                            #     }
                                            #   ]
                                            # }
                                            # and then check if the gene is available in MD
                                            mygene_info_url = '{0}query?q=chr{1}:{2}-{3}&fields=symbol&species=human'.format(md_utilities.urls['mygene.info'], res_chr['name'], positions[0], positions[1])
                                            try:
                                                mygene_response = json.loads(
                                                    http.request(
                                                        'GET',
                                                        mygene_info_url,
                                                        headers=header
                                                    ).data.decode('utf-8')
                                                )
                                            except Exception as e:
                                                close_db()
                                                if caller == 'cli':
                                                    return {'mobidetails_error': 'mygene.info API did not answer our query. We cannot map the dbSNP id {0}'}
                                                else:
                                                    md_utilities.send_error_email(
                                                        md_utilities.prepare_email_html(
                                                            'MobiDetails API error',
                                                            """
                                                            <p>mygene.info API did not answer the query dbsnp creation for {0} using
                                                            url {1}<br /> - from {2} with args: {3}</p>
                                                            """.format(
                                                                rs_id,
                                                                mygene_info_url,
                                                                os.path.basename(__file__),
                                                                e.args
                                                            )
                                                        ),
                                                        '[MobiDetails - MDAPI Error]'
                                                    )
                                                    flash(
                                                        """
                                                        mygene.info API did not answer our query. We cannot map the dbSNP id {0}.
                                                        An admin has been warned.
                                                        """.format(rs_id),
                                                        'w3-pale-red'
                                                    )
                                                    return redirect(url_for('md.index'), code=302)
                                            if "hits" in mygene_response:
                                                for hit in mygene_response['hits']:
                                                    if 'symbol' in hit:
                                                        # now we check if gene symbol can be foud in MD
                                                        curs.execute(
                                                            """
                                                            SELECT gene_symbol
                                                            FROM gene
                                                            WHERE gene_symbol = %s
                                                            """,
                                                            (hit['symbol'],)
                                                        )
                                                        res_gene = curs.fetchone()
                                                        if res_gene and \
                                                                res_gene['gene_symbol'] == hit['symbol']:
                                                            gene_symbols.append(hit['symbol'])
                                else:
                                    continue
            # do we have an intronic variant?
            if hgvs_nc and \
                    gene_symbols:
                md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_g_create'))
                headers = md_utilities.api_agent
                # headers['api_key'] = g.user['api_key']
                headers['Authorization'] = 'Bearer {0}'.format(md_utilities.get_api_key(curs))
                for var_hgvs_nc in hgvs_nc:
                    for gene_hgnc in gene_symbols:
                        data = {
                            'variant_ghgvs': urllib.parse.quote(var_hgvs_nc),
                            'gene_hgnc': gene_hgnc,
                            'caller': 'cli',
                        }
                        try:
                            md_response['{0};{1}'.format(var_hgvs_nc, gene_hgnc)] = json.loads(http.request('POST', md_api_url, headers=headers, fields=data).data.decode('utf-8'))
                        except Exception as e:
                            md_response['{0};{1}'.format(var_hgvs_nc, gene_hgnc)] = {
                                'mobidetails_error': 'MobiDetails returned an unexpected error for your request {0}: {1}'.format(rs_id, var_hgvs_nc)
                            }
                            md_utilities.send_error_email(
                                md_utilities.prepare_email_html(
                                    'MobiDetails API error',
                                    """
                                    <p>Error with MDAPI dbsnp creation for {0} ({1})<br /> - from {2} with args: {3}</p>
                                    """.format(
                                        rs_id,
                                        var_hgvs_nc,
                                        os.path.basename(__file__),
                                        e.args
                                    )
                                ),
                                '[MobiDetails - MDAPI Error]'
                            )
            if md_response:
                close_db()
                if caller == 'cli':
                    return jsonify(md_response)
                else:
                    if len(md_response) == 1:
                        for var in md_response:
                            if 'mobidetails_error' in md_response[var]:
                                flash(md_response[var]['mobidetails_error'], 'w3-pale-red')
                                return redirect(url_for('md.index'), code=302)
                            return redirect(
                                url_for(
                                    'api.variant',
                                    variant_id=md_response[var]['mobidetails_id'],
                                    caller='browser'
                                ),
                                code=302
                            )
                    else:
                        return render_template('md/variant_multiple.html', vars_rs=md_response)
            close_db()
            if caller == 'cli':
                return jsonify(mobidetails_error='Using Mutalyzer, we did not find any suitable variant corresponding to your request rs{}'.format(trunc_rs_id))
            else:
                flash(
                    """
                    Using <a href="https://www.mutalyzer.nl/snp-converter?rs_id=rs{0}", target="_blank">Mutalyzer</a>,
                    we did not find any suitable variant corresponding to your request rs{0}
                    """.format(trunc_rs_id),
                    'w3-pale-red'
                )
                return redirect(url_for('md.index'), code=302)
        else:
            close_db()
            if caller == 'cli':
                return jsonify(mobidetails_error='Invalid rs id provided')
            else:
                flash('Invalid rs id provided', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
    else:
        close_db()
        if caller == 'cli':
            return jsonify(mobidetails_error='Invalid parameter')
        else:
            flash('Invalid parameter', 'w3-pale-red')
            return redirect(url_for('md.index'), code=302)
            # return jsonify(mobidetails_error='Invalid rs id provided')
# -------------------------------------------------------------------
# api - variant create from VCF string


@bp.route('/api/variant/create_vcf_str', methods=['GET', 'POST'])
def api_create_vcf_str(genome_version='hg38', vcf_str=None, caller='browser', api_key=None):
    # check and get params
    match_vcf_str = None
    vcf_str_regexp = md_utilities.regexp['vcf_str_captured']
    if md_utilities.get_post_param(request, 'vcf_str'):
        match_vcf_str = re.search(rf'^({vcf_str_regexp})$', urllib.parse.unquote(md_utilities.get_post_param(request, 'vcf_str')))
    if md_utilities.get_post_param(request, 'caller'):
        caller = 'cli' if md_utilities.get_post_param(request, 'caller') == 'cli' else 'browser'
    if (md_utilities.get_running_mode() == 'maintenance'):
        if caller == 'cli':
            return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot annotate new variants.')
        else:
            return redirect(url_for('md.index'), code=302)
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if not g.user:
        # external API call - or non-connected user on webUI
        res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_api_key_from_request(request))
        if 'mobidetails_error' in res_check_api_key:
            close_db()
            if caller == 'cli':
                return jsonify(res_check_api_key)
            else:
                flash(res_check_api_key['mobidetails_error'], 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        else:
            g.user = res_check_api_key['mobiuser']

    header = md_utilities.api_agent
    if md_utilities.get_post_param(request, 'genome_version'):
        genome_version = md_utilities.translate_genome_version(md_utilities.get_post_param(request, 'genome_version'))
        if genome_version == 'wrong_genome_input':
            close_db()
            if caller == 'cli':
                return jsonify(mobidetails_error='The genome version provided as input is invalid.')
            else:
                flash('The genome version provided as input is invalid.', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)

    if genome_version and \
            match_vcf_str and \
            caller:
            # api_key:
        # db = get_db()
        vcf_str = match_vcf_str.group(1)
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # submit vcf_str to VV
        # then get NMXXX hgvs
        # check if NM avail in MD (and store if canonical)
        # if not canonical get 'worse nomenclature' exon>intron>UTR
        # submit vv_data to create_var_vv

        # check if variant exists
        chr, pos, ref, alt = md_utilities.decompose_vcf_str(vcf_str)
        if chr is None:
            close_db()
            if caller == 'cli':
                return jsonify(mobidetails_error='Invalid VCF string submission')
            else:
                flash('Invalid VCF string submission.', 'w3-pale-red')
                return redirect(url_for('md.index'), code=302)
        curs.execute(
            """
            SELECT a.feature_id, c.canonical, b.c_name, b.refseq
            FROM variant a, variant_feature b, gene c
            WHERE a.feature_id = b.id
                AND b.gene_symbol = c.gene_symbol
                AND b.refseq = c.refseq
                AND a.genome_version = %s
                AND a.chr = %s
                AND a.pos = %s
                AND a.pos_ref = %s
                AND a.pos_alt = %s
            """,
            (genome_version, chr, pos, ref, alt)
        )
        res_vcf = curs.fetchall()
        # check if intergenic variant (no refseq, no gene, etc)
        if not res_vcf:
            curs.execute(
                """
                SELECT feature_id
                FROM variant
                WHERE genome_version = %s
                    AND chr = %s
                    AND pos = %s
                    AND pos_ref = %s
                    AND pos_alt = %s
                """,
                (genome_version, chr, pos, ref, alt)
            )
            res_vcf = curs.fetchone()
            if res_vcf:
                var_vcf= {'intergenic_variant_1': {
                    'mobidetails_id': res_vcf['feature_id'],
                    'url': '{0}{1}'.format(
                        request.host_url[:-1],
                        url_for('api.variant', variant_id=res_vcf['feature_id'], caller='browser')
                    )
                }}
                close_db()
                if caller == 'cli':
                    return jsonify(var_vcf)
                else:
                    return redirect(url_for('api.variant', variant_id=res_vcf['feature_id'], caller='browser'), code=302)
        if res_vcf:
            # genic variant already known
            vars_vcf = {}
            for var in res_vcf:
                current_var = '{0}:c.{1}'.format(var['refseq'], var['c_name'])
                vars_vcf[current_var] = {
                    'mobidetails_id': var['feature_id'],
                    'url': '{0}{1}'.format(
                        request.host_url[:-1],
                        url_for('api.variant', variant_id=var['feature_id'], caller='browser')
                    )
                }
            close_db()
            if caller == 'cli':
                return jsonify(vars_vcf)
            else:
                if len(vars_vcf) == 1:
                    for var in res_vcf:
                        return redirect(url_for('api.variant', variant_id=var['feature_id'], caller='browser'), code=302)
                else:
                    return render_template('md/variant_multiple.html', vars_rs=vars_vcf)
                    # return redirect(url_for('md.variant_multiple', vars_rs=vars_vcf), code=302)
        else:
            # creation
            vv_base_url = md_utilities.get_vv_api_url(caller)
            # print(vv_base_url)
            if not vv_base_url:
                close_db()
                if caller == 'cli':
                    return jsonify(mobidetails_error='Variant Validator looks down!')
                else:
                    flash('Variant Validator looks down!', 'w3-pale-red')
                    return redirect(url_for('md.index'), code=302)
            genome_vv = 'GRCh38'
            if genome_version == 'hg19' or \
                    genome_version == 'GRCh37':
                genome_vv = 'GRCh37'
                # weird VV seems to work better with 'GRCh37' than with 'hg19'
            # special code for vv
            # vv_special = ''
            # # # vv_provider = md_utilities.urls['rest_vv_genuine']
            # vv_provider = md_utilities.urls['rest_vv_browser']['3']
            # # # print(vv_provider)
            # # # print(vv_base_url)
            # if re.match(rf'{vv_provider}', vv_base_url):
            #     vv_special = 'auth_'
            # vv_url = "{0}VariantValidator/variantvalidator/{1}/{2}:{3}:{4}:{5}/{6}all?content-type=application/json".format(
            #     vv_base_url, genome_vv, chr, pos, ref, alt, vv_special
            # )
            # restvv 2025 - comment all above
            vv_url = "{0}VariantValidator/variantvalidator/{1}/{2}:{3}:{4}:{5}/auth_all?content-type=application/json".format(
                vv_base_url, genome_vv, chr, pos, ref, alt
            )
            # print(vv_url)
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
                if caller == 'cli':
                    return jsonify(mobidetails_error='Variant Validator did not return any value for the variant {}.'.format(urllib.parse.unquote(vcf_str)))
                else:
                    try:
                        flash(
                            """
                            There has been an issue with the annotation of the variant via VariantValidator.
                            The error is the following: {}
                            """.format(vv_data['validation_warning_1']['validation_warnings']),
                            'w3-pale-red'
                        )
                    except Exception:
                        flash(
                            """
                            There has been an issue with the annotation of the variant via VariantValidator.
                            Sorry for the inconvenience. You may want to try again in a few minutes.
                            """,
                            'w3-pale-red'
                        )
                    return redirect(url_for('md.index'), code=302)
            vv_error = md_utilities.vv_internal_server_error(caller, vv_data, vcf_str)
            if vv_error != 'vv_ok':
                close_db()
                if caller == 'cli':
                    return jsonify(vv_error)
                else:
                    flash(vv_error)
                    return redirect(url_for('md.index'), code=302)
            # look for gene acc #
            # print(vv_data)
            var_dict = {}
            # intergenic variants
            if vv_data['flag'] == 'intergenic':
                var_dict['intergenic'] = {
                    'vv_key_var': 'intergenic_variant_1',
                    'canonical': None,
                    'genic_csq': None,
                    'RefSeq_NM': None,
                    'new_variant': None
                }
            # {gene_symbol: [hgvs_expression, can(True/False), csq(exon/intron)]}
            # we look for at least variant in a canonical isoform
            # if no canonical isoforms are found, map the variant in the "worst" isoform exon>intron>UTR
            # we must also find the gene(s)
            # print(vv_data)
            else:
                for key in vv_data.keys():
                    variant_regexp = md_utilities.regexp['variant']
                    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
                    match_obj = re.search(rf'^({ncbi_transcript_regexp}):c\.({variant_regexp})', key)
                    if match_obj:
                        new_variant = match_obj.group(2)
                        vv_refseq = match_obj.group(1)
                        # get the gene symbol
                        # test for 2 genes: 1-45340253-A-C hg38 (MUTYH, TOE1)
                        curs.execute(
                            """
                            SELECT gene_symbol, canonical
                            FROM gene
                            WHERE refseq = %s
                            """,
                            (vv_refseq,)
                        )
                        res_gene = curs.fetchone()
                        if res_gene:
                            if res_gene['canonical'] is True:
                                var_dict[res_gene['gene_symbol']] = {
                                    'vv_key_var': key,
                                    'canonical': res_gene['canonical'],
                                    'genic_csq': md_utilities.get_var_genic_csq(new_variant),
                                    'RefSeq_NM': vv_refseq,
                                    'new_variant': new_variant
                                }
                            else:
                                if (res_gene['gene_symbol'] not in var_dict) or \
                                        (
                                            res_gene['gene_symbol'] in var_dict and
                                            var_dict[res_gene['gene_symbol']]['canonical'] is False and
                                            md_utilities.is_higher_genic_csq(
                                                md_utilities.get_var_genic_csq(new_variant),
                                                var_dict[res_gene['gene_symbol']]['genic_csq']
                                            ) is True
                                        ):
                                    var_dict[res_gene['gene_symbol']] = {
                                        'vv_key_var': key,
                                        'canonical': res_gene['canonical'],
                                        'genic_csq': md_utilities.get_var_genic_csq(new_variant),
                                        'RefSeq_NM': vv_refseq,
                                        'new_variant': new_variant
                                    }
            if var_dict:
                vars_vcf = {}
                for gene in var_dict:
                    creation_dict = md_utilities.create_var_vv_vcf_str(
                        var_dict[gene]['vv_key_var'], gene, var_dict[gene]['RefSeq_NM'],
                        'c.{}'.format(var_dict[gene]['new_variant']), var_dict[gene]['new_variant'],
                        vv_data, caller, db, g
                    )
                    if isinstance(creation_dict, int):
                        # success
                        vars_vcf[var_dict[gene]['vv_key_var']] = {
                            'mobidetails_id': creation_dict,
                            'url': '{0}{1}'.format(
                                request.host_url[:-1],
                                url_for('api.variant', variant_id=creation_dict, caller='browser')
                            )
                        }
                    elif isinstance(creation_dict, str):
                        vars_vcf[var_dict[gene]['vv_key_var']] = {
                            'mobidetails_error': creation_dict
                        }
                    elif 'mobidetails_error' in creation_dict:
                        vars_vcf[var_dict[gene]['vv_key_var']] = creation_dict
                if caller == 'cli':
                    close_db()
                    return jsonify(vars_vcf)
                else:
                    close_db()
                    if len(vars_vcf) == 1:
                        for var in vars_vcf:
                            if 'mobidetails_id' in vars_vcf[var]:
                                return redirect(url_for('api.variant', variant_id=vars_vcf[var]['mobidetails_id'], caller='browser'), code=302)
                            elif 'mobidetails_error' in vars_vcf[var]:
                                flash(vars_vcf[var]['mobidetails_error'])
                            return render_template('md/unknown.html', run_mode=md_utilities.get_running_mode())
                    else:
                        return render_template('md/variant_multiple.html', vars_rs=vars_vcf)
                        # return redirect(url_for('md.variant_multiple', vars_rs=vars_vcf), code=302)
            else:
                close_db()
                if caller == 'cli':
                    return jsonify(mobidetails_error='Could not create variant {} (possibly considered as intergenic or mapping on non-conventional chromosomes, or simply the VariantValidator API is full - you mant to try again later).'.format(urllib.parse.unquote(vcf_str)), variant_validator_output=vv_data)
                else:
                    try:
                        flash(
                            """
                            There has been an issue with the annotation of the variant via VariantValidator.
                            The error is the following: {}
                            """.format(vv_data['validation_warning_1']['validation_warnings']),
                            'w3-pale-red'
                        )
                    except Exception:
                        flash(
                            """
                            This variant may not map on a coding transcript. Currently, Mobidetails does not handle variants on non-coding transcripts. Sorry for the inconvenience.
                            """,
                            'w3-pale-red'
                        )
                    return redirect(url_for('md.index'), code=302)
    close_db()
    if caller == 'cli':
        return jsonify(mobidetails_error='Invalid caller submitted')
    else:
        flash('Invalid params submitted to the API.', 'w3-pale-red')
        return redirect(url_for('md.index'), code=302)

# -------------------------------------------------------------------
# api - gene


@bp.route('/api/gene/<string:gene_hgnc>')
def api_gene(gene_hgnc=None):
    if gene_hgnc is None:
        return jsonify(mobidetails_error='No gene submitted')
    if re.search(r'[^\w\.-]', gene_hgnc):
        return jsonify(mobidetails_error='Invalid gene submitted')
    research = gene_hgnc
    search_id = 'gene_symbol'
    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
    match_obj = re.search(rf'({ncbi_transcript_regexp})', gene_hgnc)
    if match_obj:
        # we have a RefSeq accession number
        research = match_obj.group(1)
        search_id = 'refseq'
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if re.search(r'^\d+$', research):
        curs.execute(
            """
            SELECT *
            FROM gene
            WHERE hgnc_id = %s
            """,
            (research,)
        )
    else:
        curs.execute(
            """
            SELECT *
            FROM gene
            WHERE {0} = '{1}'
            """.format(search_id, research)
        )
    res = curs.fetchall()
    d_gene = {}
    if res:
        for transcript in res:
            if 'HGNC Name' not in d_gene:
                d_gene['HGNCName'] = transcript['hgnc_name']
            if 'HGNC Symbol' not in d_gene:
                d_gene['HGNCSymbol'] = transcript['gene_symbol']
                d_gene['clingenCriteriaSpec'] = md_utilities.get_clingen_criteria_specification_id(d_gene['HGNCSymbol'])
            if 'HGNC ID' not in d_gene:
                d_gene['HGNCID'] = transcript['hgnc_id']
            if 'chr' not in d_gene:
                d_gene['Chr'] = transcript['chr']
            if 'strand' not in d_gene:
                d_gene['Strand'] = transcript['strand']
            if 'ng' not in d_gene:
                if transcript['ng'] == 'NG_000000.0':
                    d_gene['RefGene'] = 'No RefGene in MobiDetails'
                else:
                    d_gene['RefGene'] = transcript['ng']
            d_gene[transcript['refseq']] = {
                'canonical': transcript['canonical'],
                'numberOfExons': transcript['number_of_exons']
            }
            if 'RefProtein' not in d_gene[transcript['refseq']]:
                if transcript['np'] == 'NP_000000.0':
                    d_gene[transcript['refseq']]['RefProtein'] = 'No RefProtein in MobiDetails'
                else:
                    d_gene[transcript['refseq']]['RefProtein'] = transcript['np']
            if 'UNIPROT' not in d_gene[transcript['refseq']]:
                d_gene[transcript['refseq']]['UNIPROT'] = transcript['uniprot_id']
            if 'proteinSize' not in d_gene[transcript['refseq']]:
                d_gene[transcript['refseq']]['proteinSize'] = transcript['prot_size']
            if 'variantCreationTag' not in d_gene[transcript['refseq']]:
                d_gene[transcript['refseq']]['variantCreationTag'] = transcript['variant_creation']
            if 'ensemblTranscript' not in d_gene[transcript['refseq']]:
                d_gene[transcript['refseq']]['ensemblTranscript'] = transcript['enst']
            if 'ensemblProtein' not in d_gene[transcript['refseq']]:
                d_gene[transcript['refseq']]['ensemblProtein'] = transcript['ensp']
        close_db()
        return jsonify(d_gene)
    else:
        close_db()
        return jsonify(mobidetails_warning='Unknown gene symbol')

# -------------------------------------------------------------------
# api - update class


@bp.route('/api/variant/update_acmg', methods=['POST'])
def api_update_acmg(variant_id=None, acmg_id=None, api_key=None):
    if (md_utilities.get_running_mode() == 'maintenance'):
        return jsonify(mobidetails_error='MobiDetails is currently in maintenance mode and cannot add new ACMG classes.')
    # check and get params
    db = get_db()
    # res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_post_param(request, 'api_key'))
    res_check_api_key = md_utilities.check_api_key(db, md_utilities.get_api_key_from_request(request))
    if 'mobidetails_error' in res_check_api_key:
        close_db()
        return jsonify(res_check_api_key)
    else:
        g.user = res_check_api_key['mobiuser']
    match_variant_id = re.search(r'^(\d+)$', str(md_utilities.get_post_param(request, 'variant_id')))
    if match_variant_id:
        variant_id = int(match_variant_id.group(1))
    match_acmg_id = re.search(r'^(\d+)$', str(md_utilities.get_post_param(request, 'acmg_id')))
    if match_acmg_id:
        acmg_id = int(match_acmg_id.group(1))
    if variant_id and \
            acmg_id:
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if acmg_id > 0 and acmg_id < 7:
            # variant exists?
            curs.execute(
                """
                SELECT id
                FROM variant_feature
                WHERE id = %s
                """,
                (variant_id,)
            )
            res = curs.fetchone()
            if res:
                # variant has already this class w/ this user?
                curs.execute(
                    """
                    SELECT variant_feature_id
                    FROM class_history
                    WHERE variant_feature_id = %s
                        AND mobiuser_id = %s
                        AND acmg_class = %s
                    """,
                    (variant_id, g.user['id'], acmg_id)
                )
                res = curs.fetchone()
                if res:
                    close_db()
                    return jsonify(mobidetails_error='ACMG class already submitted by this user for this variant')
                today = datetime.datetime.now()
                date = '{0}-{1}-{2}'.format(
                    today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
                )
                curs.execute(
                    """
                    INSERT INTO class_history (variant_feature_id, acmg_class, mobiuser_id, class_date)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (variant_id, acmg_id, g.user['id'], date)
                )
                db.commit()
                d_update = {
                    'variant_id': variant_id,
                    'new_acmg_class': acmg_id,
                    'mobiuser_id': g.user['id'],
                    'date': date
                }
                close_db()
                return jsonify(d_update)
            else:
                close_db()
                return jsonify(mobidetails_error='Invalid variant id submitted')
        else:
            close_db()
            return jsonify(mobidetails_error='Invalid ACMG class submitted')
    else:
        close_db()
        return jsonify(mobidetails_error='Invalid parameters')
