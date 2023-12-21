function defgen_export(genome, vf_id, defgen_url, csrf_token) {
	// send header for flask-wtf crsf security
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });
	$.ajax({
		type: "POST",
		url: defgen_url,
		data: {
			vfid: vf_id, genome: genome
		}
	})
	.done(function(html) {
		$('#defgen_modal_' + genome).html(html);
		$('#defgen_modal_' + genome).show();
	});
}


function litvar2(litvar_url, csrf_token) {
	//ajax for litvar
	if ($('#dbsnp_id').text() !== '') {
		// send header for flask-wtf crsf security
		$.ajaxSetup({
			beforeSend: function(xhr, settings) {
				if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
					xhr.setRequestHeader("X-CSRFToken", csrf_token);
				}
			}
		});
		$.ajax({
			type: "POST",
			url: litvar_url,
			data: {
				rsid: $('#dbsnp_id').text()
			}
		})
		.done(function(html) {
			$("#litvar_data").replaceWith(html);
		});
	}
	else {
		$("#litvar_data").replaceWith('<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">requesting LitVar2 for Pubmed requires a dbSNP identifier</div>');
	}
}


function lovd(lovd_url, genome, chrom, g_name, csrf_token) {
	// ajax for LOVD
	//send header for flask-wtf crsf security
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });
	$.ajax({
		type: "POST",
		url: lovd_url,
		data: {
			genome: genome, chrom: chrom, g_name: g_name, c_name: $('#c_name').text(), gene:$('#gene_symbol').text()
		}
        // pos: $('#pos_19').text(),
	})
	.done(function(html) {
        // selector for datatable
        var population_table = $('#population_table').DataTable();
        // prepare js table from flask html tr
        var new_rows = html.split(",");
        // remove old tr and destroy datatable
        population_table
            .row($("#lovd_feature").parents('tr'))
            .remove()
            .draw()
            .destroy();
        // add new tr and rebuilt datatable
        $.each(new_rows, function(i, item){$('#population_table tbody').append(item);});
        redraw_dt('population_table', false);
	});
}


function intervar(intervar_url, csrf_token) {
	// ajax for intervar
	if ($('#dna_type').text() == 'substitution' && $('#segment_type').text() == 'exon' && $('#hgvs_p_name').text() != 'p.(?)' && $('#hgvs_p_name').text() != 'p.(Met1?)') {
		// send header for flask-wtf crsf security
		$.ajaxSetup({
			beforeSend: function(xhr, settings) {
				if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
					xhr.setRequestHeader("X-CSRFToken", csrf_token);
				}
			}
		});
		$.ajax({
			type: "POST",
			url: intervar_url,
			data: {
				// genome: $('#genome_19').text(), chrom: $('#chrom_19').text(), pos: $('#pos_19').text(), ref: $('#ref_19').text(), alt: $('#alt_19').text(), gene:$('#gene_symbol').text()
        genome: $('#genome_38').text(), chrom: $('#chrom_38').text(), pos: $('#pos_38').text(), ref: $('#ref_38').text(), alt: $('#alt_38').text(), gene:$('#gene_symbol').text()
			}
		})
		.done(function(html) {
			$('#intervar_data').replaceWith(html);
      redraw_dt('population_table', true);
		});
	}
}


function spliceaivisual(spliceaivisual_url, static_path, caller, csrf_token) {
  // ajax for spliceaivisual
  // send header for flask-wtf crsf security
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    }
  });
  $.ajax({
    type: "POST",
    url: spliceaivisual_url,
    data: {
      chrom: $('#chrom_38').text(), pos: $('#pos_38').text(), ref: $('#ref_38').text(), alt: $('#alt_38').text(), ncbi_transcript: $('#nm_acc').text(), strand: $('#strand').text(), variant_id: $('#variant_id').val(), gene_symbol: $('#gene_symbol').text(), caller: caller
    }
  })
  .done(function(spliceaivisual_response) {
    // $('#igv_com').replaceWith('<span></span>');
    if (spliceaivisual_response == '<p style="color:red">Bad params for SpliceAI-visual.</p>') {
      $('#igv_com').replaceWith(spliceaivisual_response);
    }
    else if (spliceaivisual_response == '<p style="color:red">SpliceAI-visual is currently not available for this transcript.</p>') {
      $('#igv_com').replaceWith(spliceaivisual_response);
    }
    else if (spliceaivisual_response == '<p style="color:red">Failed to establish a connection to the SpliceAI-visual server.</p>') {
      $('#igv_com').replaceWith(spliceaivisual_response);
    }
    else {
      $('#igv_com').replaceWith('<span></span>');
      $('#igv_desc').show();
      if (caller == 'automatic') {
        var options =
          {
            showNavigation: true,
            showRuler: true,
            showCenterGuide: true,
            showCursorTrackingGuide: true,
            //genome: 'hg38',
            locus: 'chr' + $('#chrom_38').text() + ':'+ $('#pos_38').text() + '-' + $('#pos_38').text(),
            reference: {
              id: "hg38",
              name: "Human (GRCh38/hg38)",
              fastaURL: static_path + "resources/genome/hg38.fa.gz",
              indexURL: static_path + "resources/genome/hg38.fa.gz.fai",
              compressedIndexURL: static_path + "resources/genome/hg38.fa.gz.gzi",
              cytobandURL: static_path + "resources/genome/cytoBandIdeo.txt.gz"
            },
            tracks: [
              // { // uncompressed version
              //   name: 'SpliceAI WT ' + $('#nm_acc').text(),
              //   format: 'bedGraph',
              //   url: static_path + 'resources/spliceai/transcripts/' + $('#nm_acc').text() + '.bedGraph',
              //   indexed: false,
              //   removable: false,
              //   label: 'SpliceAI raw scores for ' + $('#nm_acc').text(),
              //   roi: [{
              //     name: $('#variant_id').text(),
              //     url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '.bed',
              //     indexed: false,
              //     color: "rgba(0, 150, 50, 0.25)"
              //   }]
              // },
              { // compressed version
                name: 'SpliceAI WT ' + $('#nm_acc').text(),
                type: 'wig',
                format: 'bedGraph',
                url: static_path + 'resources/spliceai/transcripts/' + $('#nm_acc').text() + '.bedGraph.gz',
                indexURL: static_path + 'resources/spliceai/transcripts/' + $('#nm_acc').text() + '.bedGraph.gz.tbi',
                removable: false,
                label: 'SpliceAI raw scores for ' + $('#nm_acc').text(),
                roi: [{
                  name: $('#variant_id').text(),
                  url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '.bed',
                  indexed: false,
                  color: "rgba(0, 150, 50, 0.25)"
                }]
              },
              {
                name: 'SpliceAI MT ' + $('#nm_acc').text(),
                type: 'wig',
                format: 'bedgraph',
                url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '.bedGraph.gz',
                indexURL: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '.bedGraph.gz.tbi',
                removable: false,
                label: 'SpliceAI raw scores for ' + $('#nm_acc').text(),
                roi: [{
                  name: $('#variant_id').text(),
                  url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '.bed',
                  indexed: false,
                  color: "rgba(220, 20, 60, 0.25)"
                }]           
              },
              {
                name: 'Inserted nucleotides',
                type: 'wig',
                format: 'bedGraph',
                url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '_ins.bedGraph.gz',
                indexURL: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '_ins.bedGraph.gz.tbi',
                label: 'Insertion track',
                roi: [{
                  name: $('#variant_id').text(),
                  url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '_ins.bed',
                  indexed: false,
                  color: "rgba(220, 20, 60, 0.25)"
                }]
              },
              {
                name: 'MANE transcripts',
                url: static_path + 'resources/mane/MANE.GRCh38.v1.0.refseq.bb',
                indexed: false,
                label: 'MANE transcripts',
              },
              {
                name: 'Refseq Genes',
                url: static_path + 'resources/genome/refGene.txt.gz',
                order: 1000000,
                indexed: false
              }
            ]
          };
        igv.createBrowser(document.getElementById('igv_div'), options)
          .then(function (browser) {
              igv.browser = browser;
              if (spliceaivisual_response == 'full') {
                // load full transcript track
                add_full_gene_track(static_path);
              }
              if ($('#morfee_table').length) {
                // if we have morfeedb results we should have a bed describing ORFs
                add_morfee_bed_track(static_path)          
              }
          });
      }
      else if ($('#igv_div').length && igv.browser) {
        add_full_gene_track(static_path);
      }
      if ($('#spliceai_visual_full_gene').is(':hidden') && spliceaivisual_response == 'ok') {
        $('#spliceai_visual_full_gene').show();
      }
      else {
        $('#spliceai_visual_full_gene').hide();
      }
    }
  });
}


async function add_full_gene_track(static_path) {
  igv.browser.loadTrack({
    name: 'FULL MT SpliceAI ' + $('#nm_acc').text(),
    type: 'wig',
    format: 'bedGraph',
    url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '_full_transcript.bedGraph.gz',
    indexURL: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '_full_transcript.bedGraph.gz.tbi',
    label: 'SpliceAI raw scores for full mutant ' + $('#nm_acc').text(),
    removable: false,
    order: 3,
    roi: [{
      name: $('#variant_id').text(),
      url: static_path + 'resources/spliceai/variants/' + $('#variant_id').val() + '.bed',
      indexed: false,
      color: "rgba(220, 20, 60, 0.25)"
    }]
  });
  $('#full_transcript_download').html(' or <a href="' + escape(static_path) + 'resources/spliceai/variants/' + escape($('#variant_id').val()) + '_full_transcript.bedGraph.gz" target="_blank">full mutant transcript</a>');
  $('#spliceai_visual_full_wheel').html('<span></span>');
  $('html').css('cursor', 'default');
}


async function add_morfee_bed_track(static_path) {
  // igv.browser.loadTrack({
  //   name: 'upORF: MORFEEDB',
  //   type: 'annotation',
  //   format: 'bed',
  //   indexed: false,
  //   autoHeight: true,
  //   url: static_path + 'resources/morfeedb/variants/' + $('#variant_id').val() + '.bed',
  //   label: 'MORFEEDB predicted upORFs for ' + $('#c_name').text(),
  //   removable: false,
  //   order: 3,
  //   color: "rgba(220, 20, 60, 0.25)"
  // });
  igv.browser.loadTrack({
    name: 'upORF: MORFEEDB',
    type: 'annotation',
    format: 'gtf',
    displayMode: "expanded",
    indexed: false,
    autoHeight: true,
    url: static_path + 'resources/morfeedb/variants/' + $('#variant_id').val() + '.gtf',
    label: 'MORFEEDB predicted upORFs for ' + $('#c_name').text(),
    removable: false,
    order: 3,
    colorBy: "orfSNVs_type",
    colorTable: {
       "uTIS": "rgba(153, 0, 0, 0.25)",
       "uSTOP": "rgba(255, 128, 0, 0.25)",
       "new_uSTOP": "rgba(220, 20, 60, 0.25)",
    }
  });
}


function modify_class(variant_id, mobiuser_id, modify_class_url, csrf_token) {
	// ajax to modify variant class
  $('html').css('cursor', 'progress');
  $('.w3-button').css('cursor', 'progress');
  $('.w3-modal').css('cursor', 'progress');
  $('#sub').prop('disabled', true);
  var html_comment = $("#acmg_comment").val().replace(/\r\n|\r|\n/g,"<br />");
  html_comment = escape(html_comment);
  // html_comment = html_comment.replace(/'/g,"\'");
  // alert(html_comment);
	// html_comment = encodeURIComponent(html_comment);
  var acmg = $("#acmg_select").val();
	// send header for flask-wtf crsf security
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    }
  });
	$.ajax({
		type: "POST",
		url: modify_class_url,
		data: {
			variant_id: variant_id, acmg_select: acmg, acmg_comment: html_comment
		}
	})
	.done(function(tr_html) {
    var reg = /something went wrong with the addition of this annotation/;
    if (!reg.test(tr_html)) {
	  // if (tr_html !== 'notok') {
  	  var re = /already_classified/;
      // alert("#" + mobiuser_id + "-" + acmg + "-" + variant_id);
  		if ($("#" + mobiuser_id + "-" + acmg + "-" + variant_id).length > 0 ) {
  			if (!re.test(tr_html)) {
  				$("#" + mobiuser_id + "-" + acmg + "-" + variant_id).hide();
  			}
  			// else {
  			// 	$("#" + mobiuser_id + "-" + acmg + "-" + variant_id).css('font-weight', 'bold');
  			// }
      }
  		if ($("#already_classified").length > 0) {
        $("#already_classified").remove();
      }
      // var table_class = $('#class_table').DataTable();
      $('#class_table').DataTable().destroy();
      $("#class_table>tbody:last").append(unescape(tr_html));
  		$("#" + mobiuser_id + "-" + acmg + "-" + variant_id).css('font-weight', 'bold');
  		$("#acmg_comment").val('');
  		if ($("#no_class").length > 0) {
        // $("#no_class").hide();
        $('#class_table').DataTable()
          .row($('#no_class'))
          .remove()
          .draw()
          .destroy();
      }
      if ($("#owner_username").text() == 'mobidetails' && $("#current_user").text() != 'mobidetails') {
        $("#owner_username").text($("#current_user").text());
      }
      redraw_dt('class_table', false);
    }
	  else {
		     $("#message_return").html(tr_html);
	  }
    $('html').css('cursor', 'default');
    $('.w3-button').css('cursor', 'default');
    $('.w3-modal').css('cursor', 'default');
    $('#sub').prop('disabled', false);
    $("#modify_class_modal").hide();
	});
}


function remove_class(variant_id, mobiuser_id, acmg_class, remove_class_url, csrf_token) {
	// ajax to remove variant class
	// send header for flask-wtf crsf security
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    }
  });
	$.ajax({
		type: "POST",
		url: remove_class_url,
		data: {
			variant_id: variant_id, acmg_class: acmg_class
		}
	})
	.done(function(return_code) {
		if (return_code == 'ok') {
      $('#class_table').DataTable()
        .row($("#"+mobiuser_id+"-"+acmg_class+"-"+variant_id))
        .remove()
        .draw();
      // $("#"+mobiuser_id+"-"+acmg_class+"-"+variant_id).remove();
    }
		else {
			$("#message_return").html(return_code);
		}
	});
}


function send_var_message(url, csrf_token) {
   // ajax to send email
	var html_message = $("#message_body").val().replace(/\r\n|\r|\n/g,"<br />");
  // alert(html_message);
  $('html').css('cursor', 'progress');
	$('.w3-button').css('cursor', 'progress');
  $('.w3-modal').css('cursor', 'progress');
  $('#sub_message').prop('disabled', true);
	// send header for flask-wtf crsf security
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    }
  });
	$.ajax({
		type: "POST",
		url: url,
		data: {
			receiver_id: $("#receiver_id").val(), message: html_message, message_object: $("#message_object").text()
		}
	})
	.done(function(return_code) {
		$("#message_return").html(return_code);
    $('html').css('cursor', 'default');
    $('.w3-button').css('cursor', 'default');
    $('.w3-modal').css('cursor', 'default');
		$("#message_modal").hide();
    $('#sub_message').prop('disabled', false);
	});
}


function run_spip(url, variant_id, csrf_token) {
	// send header for flask-wtf crsf security
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    }
  });
	$.ajax({
		type: "POST",
		url: url,
		data: {
			gene_symbol: $('#gene_symbol').text(), nm_acc: $('#nm_acc').text(), c_name: $('#c_name').text(), variant_id: variant_id
		}
	})
	.done(function(spip_result) {
		$("#spip").html(spip_result);
    datatable = $('#spip_summary').DataTable({
      responsive: true,
      dom: 't',
      "order": [],
      buttons: [
             'copy', 'excel', 'pdf'
      ]
    });
    if ($('#spip_interpretation').html() !== 'Not available') {
      datatable = $('#spip_full').DataTable({
        responsive: true,
        dom: 't',
        pageLength: 25,
        "order": []
      });
    }
	});
}

function redraw_dt(dtid, destroy) {
  if (destroy) {
    $('#' + dtid).DataTable().destroy();
  } 
  $('#' + dtid).DataTable({
      responsive: true,
      dom: 't',
      "pageLength": 25,
      "order": []
  });
}

function clingen_evrepo(clingen_evrepo_api_url, variant, contact_url) {
  $.ajax({
		type: "GET",
		url: clingen_evrepo_api_url + "interpretations?hgvs=" + encodeURIComponent(variant),
  })
	.done(function(jsonResponse) {
    if ($.isEmptyObject(jsonResponse.variantInterpretations)) {
      $('#clingen_evrepo').replaceWith("This variant has not yet been assessed by the ClinGen experts groups.");
    }
    else if (! $.isEmptyObject(jsonResponse.variantInterpretations[0].guidelines[0].outcome.label)) {
      var clingen_evrepo_url = jsonResponse.variantInterpretations[0]['@id']
      $('#clingen_evrepo').replaceWith("<a href='" + clingen_evrepo_url.replace("/api/", "/ui/") + "' target='_blank'>" + jsonResponse.variantInterpretations[0].guidelines[0].outcome.label + "</a>");
    }
    else {
      $('#clingen_evrepo').replaceWith("Error when parsing the data from ClinGen: you may want to warn an admin (<a href='" + contact_url + "' target = '_blank'>contact</a>)");
    }
    redraw_dt('population_table', true);
  })
  .fail(function() {
    $('#clingen_evrepo').replaceWith("The ClinGen website is unreachable for some reason.");
    redraw_dt('population_table', true);
  });
}

function spliceai_lookup(spliceai_lookup_url, csrf_token) {
	// ajax for spliceai lookup
	// send header for flask-wtf crsf security
	$.ajaxSetup({
		beforeSend: function(xhr, settings) {
			if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
				xhr.setRequestHeader("X-CSRFToken", csrf_token);
			}
		}
	});
	$.ajax({
		type: "POST",
		url: spliceai_lookup_url,
		data: {
			variant: "chr" + $('#chrom_38').text() + "-" + $('#pos_38').text() + "-" + $('#ref_38').text() + "-" + $('#alt_38').text(), transcript: $('#nm_acc').text()
		}
	})
	.done(function(spliceai_result) {
    var re = /spliceAI lookup API/;
    if (!re.test(spliceai_result)) {
      var spliceai_split = spliceai_result.split(';');
  		$("#spliceai_lookup_ag").html(spliceai_lookup_html(spliceai_split[0]));
      $("#spliceai_lookup_al").html(spliceai_lookup_html(spliceai_split[1]));
      $("#spliceai_lookup_dg").html(spliceai_lookup_html(spliceai_split[2]));
      $("#spliceai_lookup_dl").html(spliceai_lookup_html(spliceai_split[3]));
      $("#spliceai_lookup_ag_tr").show();
      $("#spliceai_lookup_al_tr").show();
      $("#spliceai_lookup_dg_tr").show();
      $("#spliceai_lookup_dl_tr").show();
    }
    else {
      $("#spliceai_lookup_ag").html(spliceai_result);
      $("#spliceai_lookup_ag_tr").show();
    }
    if ($.fn.DataTable.isDataTable('#splicing_table')) {
      redraw_dt('splicing_table', true);
    }
    else {
      redraw_dt('splicing_table', false);
    }
    $('#splicing_table').show();
    $('#spliceai_lookup_wheel').empty();
    $('#spliceai_lookup_button').hide();
    $('html').css('cursor', 'default');
	});
}

function spliceai_lookup_html(spliceai_str) {
  var split_str = spliceai_str.split(" ");
  var totest = parseFloat(split_str[0]);
  if (!isNaN(totest)) {
    if (totest < 0.2) {color_style = '#00A020'}
    else if (totest > 0.8) {color_style = '#FF0000'}
    else if (totest > 0.5) {color_style = '#FF6020'}
    else if (totest > 0.2) {color_style = '#FFA020'}
    return '<span style="color:' + color_style + ';">' + split_str[0] + '</span>&nbsp;<span>' + split_str[1]+ '</span>';
  }
  return spliceai_str;
}

function submit_create_var_g(create_g_url, api_key, current_id, csrf_token) {
  // send header for flask-wtf crsf security
	$.ajaxSetup({
		beforeSend: function(xhr, settings) {
			if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
				xhr.setRequestHeader("X-CSRFToken", csrf_token);
			}
		}
	});
	$.ajax({
		type: "POST",
		url: create_g_url,
		data: {
			variant_ghgvs: $('#hgvs_strict_genomic_hg38').text() , gene_hgnc: $('#gene_symbol').text(), caller: 'cli', api_key: api_key
		}
	})
  .done(function(var_json) {
    if (var_json.mobidetails_error) {
      $('#result_display').html(var_json.mobidetails_error)
    }
    else if (parseInt(current_id) !== parseInt(var_json.mobidetails_id)) {
      $('#result_display').html("<a href='" + var_json.url + "' target='_blank'>Check this variant on the canonical isoform</a>")
    }
    else {
      $('#result_display').html("Mapping this variant on the canonical isoform of <em>" + encodeURIComponent($('#gene_symbol').text()) + "</em> is not possible.");
    }
    }
  );
}


function clinvar_watch(vf_id, operation, watch_url, csrf_token) {
  var swal_title = 'Add this variant to your clinvar watch list';
	var swalt_text = 'This list of variants will be checked against each new release of ClinVar, and significant changes will be reported by email to you';
	var swal_confirm = 'Yes, add it!';
	var swal_done = 'This pop-up will close automatically.';
	if (operation === 'remove') {
		var swal_title = 'Remove this variant from your clinvar watch list';
		var swalt_text = 'You can add it again later if needed';
		var swal_confirm = 'Yes, remove it!';
	}
  Swal.fire({
		title: swal_title,
		text: swalt_text,
		icon: 'warning',
		showCancelButton: true,
		confirmButtonColor: '#3085d6',
		cancelButtonColor: '#d33',
		confirmButtonText: swal_confirm
	}).then((result) => {
    if (result.isConfirmed) {
      // send header for flask-wtf crsf security
      $.ajaxSetup({
          beforeSend: function(xhr, settings) {
              if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                  xhr.setRequestHeader("X-CSRFToken", csrf_token);
              }
          }
      });
      $.ajax({
        type: "POST",
        url: watch_url,
        data: {
          vf_id: vf_id, marker: $('#clinvar_watch_span').attr('name'), clinvar_watch: 1
        }
      })
      .done(function() {
        if ($('#clinvar_watch_span').attr('name') === 'mark') {
          $('#clinvar_watch_span').on('click', function() {clinvar_watch(vf_id , 'remove', watch_url, csrf_token)});
          $('#clinvar_watch').toggleClass('fa-heart fa-heart-o');
          $('#clinvar_watch_span').attr('title', 'Unwatch this variant!');
          $('#clinvar_watch_span').attr('name', 'unmark');
          $('#clinvar_watch_heart').show();          
        }
        else {
          $('#clinvar_watch_span').on('click', function() {clinvar_watch(vf_id , 'add', watch_url, csrf_token)});
          $('#clinvar_watch').toggleClass('fa-heart-o fa-heart');
          $('#clinvar_watch_span').attr('title', 'Watch this variant!');
          $('#clinvar_watch_span').attr('name', 'mark');
          $('#clinvar_watch_heart').hide();
        }
      });
      Swal.fire({
				title: 'Done!',
				html: swal_done,
        timer: 1000,
        timerProgressBar: true,
        didOpen: () => {
          Swal.showLoading()
        },
      });
		}
	})
}


function myAccFunc(acc_id, icon_id) {
	// adapted from https://www.w3schools.com/w3css/tryit.asp?filename=tryw3css_sidebar_accordion
	var x = document.getElementById(acc_id);
	if (x.className.indexOf("w3-show") == -1) {
		// x.className += " w3-show";
		$('#' + acc_id).removeClass("w3-hide").addClass("w3-show");
		x.previousElementSibling.className += " w3-blue";
		$('#' + icon_id).removeClass("fa-caret-right").addClass("fa-caret-down");
	} else {
		// x.className = x.className.replace(" w3-show", "");
		$('#' + acc_id).removeClass("w3-show").addClass("w3-hide");
		x.previousElementSibling.className =
		x.previousElementSibling.className.replace(" w3-blue", "");
		$('#' + icon_id).removeClass("fa-caret-down").addClass("fa-caret-right");
	}
}

// https://stackoverflow.com/questions/5684303/javascript-window-open-pass-values-using-post
// function to send POST form and open it in new window

//function openWindowWithPost(url, data) {
//    var form = document.createElement("form");
//    form.target = "_blank";
//    form.method = "POST";
//    form.action = url;
//    form.style.display = "none";
//
//    for (var key in data) {
//        var input = document.createElement("input");
//        input.type = "hidden";
//        input.name = key;
//        input.value = data[key];
//        form.appendChild(input);
//    }
//
//    document.body.appendChild(form);
//    form.submit();
//    document.body.removeChild(form);
//}


// https://www.chartjs.org/docs/latest/general/responsive.html#important-note
function beforePrintHandler () {
  for (var id in Chart.instances) {
    Chart.instances[id].resize();
  }
}


$(document).ready(function() {
  $('#third_br').remove();
  if ($(window).width() < 600) {
  	$('#page_menu').remove();
    $('#second_br').remove();
    // hide left menu items
    if ($('#somatic_acc').length) {
  	  myAccFunc('hg19_acc', 'hg19_icon');
    }
  	myAccFunc('hg38_acc', 'hg38_icon');
    if ($('#somatic_acc').length) {
      myAccFunc('somatic_acc', 'somatic_icon');
    }
    if ($('#bonus_acc').length) {
      myAccFunc('bonus_acc', 'bonus_icon');
    }    
  	$('#smart_menu').hide();
  	$('#openNav').css('visibility', 'visible');
  	$('#global_content').animate({marginLeft: '0%'});
  	$('#mobile_var_name').show();
  	$('#defgen_hg19').remove();
  	$('#defgen_hg38').remove();
  }
  else if ($(window).width() < 900) {
    $('#second_br').remove();
    $('#smart_menu').find('a').removeClass('w3-large').addClass('w3-medium');
    $('#smart_menu').find('button').removeClass('w3-large').addClass('w3-medium');
    $('#smart_menu').find('span').removeClass('w3-large').addClass('w3-medium');
    $('#smart_menu').children().removeClass('w3-xxlarge').addClass('w3-medium');
    $('#global_content').animate({marginLeft: '25%'});
  	$('#smart_menu').width('25%');
  }
  else if($(window).width() < 1300) {
    $('#smart_menu').find('a').removeClass('w3-large').addClass('w3-medium');
    $('#smart_menu').find('button').removeClass('w3-large').addClass('w3-medium');
    $('#smart_menu').find('span').removeClass('w3-large').addClass('w3-medium');
    $('#smart_menu').children().removeClass('w3-xxlarge').addClass('w3-medium');
    if ($('#login_name').length) {$('#login_name').remove();}
  }

  // transform all tables as datatables
	$('.w3-table').DataTable({
  	responsive: true,
  	dom: 't',
  	"order": [],
    "pageLength": 35,
  	//scrollY: 600,
  	buttons: [
  		'copy', 'excel', 'pdf'
  	]
	});
  // deal with dbscSNV/spliceai table which can be empty
  if (!$('#spliceai_ag_50_tr').length && !$('#dbscsnvada').length && !$('#dbscsnvrf').length && !$('#absplice_max').length && !$('#no_absplice_max').length) {
    $('#splicing_table').hide();
    $('#splicing_table').DataTable().destroy();
  }

  // check MuPIT for available 3D structure - removed 20220511
  // if ($('#missense').length) {
  //   // alert($('#mupit_url').text() + "/rest/showstructure/check?pos=chr" + $('#chrom_38').text() + " " + $('#pos_38').text());
  //   $.ajax({
  // 	  type: "GET",
  // 	  url: $('#mupit_url').text() + "/rest/showstructure/check?pos=chr" + $('#chrom_38').text() + " " + $('#pos_38').text(),
  // 	})
  // 	.done(function(mupit_results) {
  //     // alert(mupit_results.hit);
  //     if (mupit_results.hit === true) {
  //         $('#mupit_link').show();
  //     }
  //   });
  // }

  // trick to force charts.js script execution and to get canvas in pdf export
  // charts are displayed by default and then quickly hidden
  $('#radar_splicing_modal').hide();
  $('#radar_missense_modal').hide();

  function convert_dt(config, table_id, table_title, table_title_style, doc) {
    var dt = $('#' + table_id).DataTable();
    var data = dt.buttons.exportData(config.exportOptions);
    // var info = dt.buttons.exportInfo(config);
    var rows = [];
    if (config.header) {
      rows.push($.map(data.header, function(d) {
        return {
          text: typeof d === 'string' ? d : d + '',
          style: 'tableHeader'
        };
      }));
    }
    for (var i = 0, ien = data.body.length; i < ien; i++) {
      rows.push($.map(data.body[i], function(d) {
        var color_style = '#000000';
        if (table_title === 'Missense predictions'){
          if (d === 'Damaging' || d === 'Probably Damaging' || d === 'Likely Pathogenic') {color_style = '#FF0000'}
          else if (d === 'Possibly Damaging') {color_style = '#FF6020'}
          else if (d === 'Tolerated' || d === 'Neutral' || d === 'Benign' || d === 'Likely Benign') {color_style = '#00A020'}
        }
        else if (table_title === 'dbscSNV, SpliceAI and AbSplice'){
          // we need to split str to get actual spliceAI values
          var split_str = d.split(" ");
          var re = /^\d\.\d{2}$/;
          var totest = parseFloat(split_str[0]);
          if (!isNaN(totest) && re.test(split_str[0])) {
            if (totest < 0.2) {color_style = '#00A020'}
            else if (totest > 0.8) {color_style = '#FF0000'}
            else if (totest > 0.5) {color_style = '#FF6020'}
            else if (totest >= 0.2) {color_style = '#FFA020'}
          }
          else if (!isNaN(totest)) {
            if (totest < 0.01) {color_style = '#00A020'}
            else if (totest > 0.2) {color_style = '#FF0000'}
            else if (totest > 0.05) {color_style = '#FF6020'}
            else if (totest >= 0.01) {color_style = '#FFA020'}
          }
          // if (! isNan(parseFloat(split_str[0])) && parseFloat(split_str[0]) < 0.2) {color_style = '#00A020'}
          // else if (! isNan(parseFloat(split_str[0])) && parseFloat(split_str[0]) > 0.8) {color_style = '#FF0000'}
          // else if (! isNan(parseFloat(split_str[0])) && parseFloat(split_str[0]) > 0.5) {color_style = '#FF6020'}
          // else if (! isNan(parseFloat(split_str[0])) && parseFloat(split_str[0]) > 0.2) {color_style = '#FFA020'}
        }
        else if (table_title === 'Positions'){
          // we need to split str to get actual metadome values
          var split_str = d.split(/[:-]+/);
          if (split_str[1] === '  	 		highly intolerant 	  ') {color_style = '#D7191C'}
          else if (split_str[1] === '  	 		intolerant 	  ') {color_style = '#FF0000'}
          else if (split_str[1] === '  	 		slightly intolerant 	  ') {color_style = '#00CCBC'}
          else if (split_str[1] === '  	 		neutral 	  ') {color_style = '#F9D057'}
          else if (split_str[1] === '  	 		slightly tolerant  	  ') {color_style = '#00CCBC'}
          else if (split_str[1] === '  	 		tolerant 	  ') {color_style = '#2E64FE'}
          else if (split_str[1] === '  	 		highly tolerant 	  ') {color_style = '#0404B4'}
        }
        else if (table_title === 'Population frequencies and databases') {
          var re = /Likely[\s_][Bb]enign/;
          if (re.test(d)) {color_style = '#0000A0'}
          re = /^Benign\s?\*{0,4}$/;
          if (re.test(d)) {color_style = '#00A020'}
          re = /Likely[\s_][Pp]athogenic/;
          if (re.test(d)) {color_style = '#FF6020'}
          re = /^Pathogenic\s?\*{0,4}$/;
          if (re.test(d)) {color_style = '#FF0000'}
        }
        else if (table_title === 'Overall predictions'){
          if (d === 'High missense' || d === 'Clinvar pathogenic' || d === 'High splice' || d === 'nonsense' || d === 'frameshift') {color_style = '#FF0000'}
          if (d === 'Moderate missense' || d === 'Moderate splice') {color_style = '#FF6020'}
          if (d === 'Low missense' || d === 'Low splice' || d ==='Splice indel') {color_style = '#FFA020'}
        }
        else if (table_title === 'Classification history' || table_title === 'Epigenetic signature') {
          var split_str = d.split(" ");
          if (split_str[1] === '5') {color_style = '#FF0000'}
          else if (split_str[1] === '4') {color_style = '#FF6020'}
          else if (split_str[1] === '3') {color_style = '#969696'}
          else if (split_str[1] === '2') {color_style = '#0000A0'}
          else if (split_str[1] === '1') {color_style = '#00A020'}
        }
        return {
          text: typeof d === 'string' ? d : d + '',
          style: i % 2 ? 'tableBodyEven'  : 'tableBodyOdd',
          color: color_style
        };
      }));
    }
    if (config.footer && data.footer) {
      rows.push($.map(data.footer, function(d) {
        return {
          text: typeof d === 'string' ? d : d + '',
          style: 'tableFooter'
        };
      }));
    }
    // return rows;
    doc['content'].push(
      " ",
      {text: table_title, style: table_title_style, tocItem: true},
      " ", {
        table: {
          headerRows: 1,
          body: rows
        },
        layout: 'noBorders'
      }
    );
    return doc;
  }
  function addZero(i) {
    if (i < 10) {
      i = "0" + i;
    }
    return i;
  }
  function formatDate() {
    var d = new Date();
    //var x = document.getElementById("demo");
    var h = addZero(d.getHours());
    var m = addZero(d.getMinutes());
    var s = addZero(d.getSeconds());
    var js_date = "MobiDetails accessed " + d.toLocaleDateString();
    var js_time = " - " + h + ":" + m + ":" + s;
    return js_date + js_time;// + "-" h + ":" + m + ":" + s;
  }

	// adapted from https://sharepoint.stackexchange.com/questions/234464/datatables-plugin-print-multiple-tables-on-one-page
  // uses pdfMake https://pdfmake.github.io/docs
  // http://pdfmake.org/#/gettingstarted
	// export multiple tables in one single pdf

	$('#ExportPdf').on("click", function() {
		var config = {
  			className: "buttons-pdf buttons-html5",
  			customize: null,
  			download: "download",
  			exportOptions: {},
  			extension: ".pdf",
  			filename: "*",
  			footer: false,
  			header: true,
  			messageBottom: "*",
  			messagetop: "*",
  			namespace: ".dt-button-2",
  			orientation: "portrait",
  			pageSize: "A4",
  			title: "*",
        author:"MobiDetails",
		};


    var doc = {
			pageSize: config.pageSize,
			pageOrientation: config.orientation,
      footer: function(currentPage, pageCount) {
        return {
          margin:10,
          alignment: 'right',
          text: currentPage.toString() + ' of ' + pageCount
        }
      },
      header: function() {
        return {
          margin:10,
          alignment: 'right',
          text: formatDate()
        }
      },
			content: [
        " ",
        " ",
        {
          toc: {
            title: {text: "Table of Content", style: 'table_title'},
          }
        },
        " ",
        " ",
        {text: "Click on a page number to get to the corresponding page (i.e. page numbers are clickable ;) ).", pageBreak: "after"}
      ],
			styles: {
				tableHeader: {
					bold: true,
					fontSize: 11,
					color: 'white',
					fillColor: '#2d4154',
					alignment: 'center'
				},
				tableBodyEven: {},
				tableBodyOdd: {
					fillColor: '#f3f3f3'
				},
        damaging: {
          color: '#ff0000'
        },
				tableFooter: {
					bold: true,
					fontSize: 11,
					color: 'white',
					fillColor: '#2d4154'
				},
				title: {
					alignment: 'center',
					fontSize: 14
				},
        table_title: {
          fontSize: 12,
          bold: true,
        },
        table_subtitle: {
          fontSize: 12,
          italics: true,
        },
				message: {},
			},
			defaultStyle: {
				fontSize: 9
			}
		};
    if ($("#nomenclature_table").length) {
      var dt = $('#nomenclature_table').DataTable();
      var info = dt.buttons.exportInfo(config);
      doc = convert_dt(config, "nomenclature_table", "Nomenclatures", "table_title", doc);
    }
    if ($("#position_table").length) {
      doc = convert_dt(config, "position_table", "Positions", "table_title", doc);
    }
    if ($("#population_table").length) {
      doc = convert_dt(config, "population_table", "Population frequencies and databases", "table_title", doc);
    }
    if ($("#prediction_table").length) {
      doc = convert_dt(config, "prediction_table", "Overall predictions", "table_title", doc);
    }
    if ($("#prediction_table_").length) {
      doc = convert_dt(config, "prediction_table", "Positions", "table_title", doc);
    }
    if ($('#segment_drawing').length) {
      var segment_image = document.querySelector('#segment_drawing').toDataURL();
      doc['content'].push(
        " ",
        {text: "Splicing context and predictions", style: "table_title", tocItem: true},
        " ",
        {image: segment_image, width: 350, alignment: 'center'}
      );
    }
    if ($('#maxent5ss_table').length) {
      doc = convert_dt(config, "maxent5ss_table", "MaxEntScan 5'ss", "table_subtitle", doc);
    }
    if ($('#maxent3ss_table').length) {
      doc = convert_dt(config, "maxent3ss_table", "MaxEntScan 3'ss", "table_subtitle", doc);
    }
    if ($('#spip_summary').length) {
      doc = convert_dt(config, "spip_summary", "SPiP summary", "table_subtitle", doc);
    }
    if ($('#spip_full').length) {
      doc = convert_dt(config, "spip_full", "Full SPiP results", "table_subtitle", doc);
    }
    if ($('#splicing_radar').width() > 0) {
      // attempt to transform radars into pdf
      var splicing_radar_image = document.querySelector('#splicing_radar').toDataURL();
      doc['content'].push(
        " ",
        {text: "Splicing radar:", style: "table_subtitle"},
        "Values are normalised (0-1), 0 being the less damaging and 1 the most for each predictor.",
        {image: splicing_radar_image, width: 350, alignment: 'center'}
      );
    }
    if ($.fn.DataTable.isDataTable('#splicing_table')) {
      doc = convert_dt(config, "splicing_table", "dbscSNV, SpliceAI and AbSplice", "table_subtitle", doc);
    }
    if ($('#absplice_bar').width() > 0) {
      // attempt to transform bar charts into pdf
      var absplice_bar_chart = document.querySelector('#absplice_bar').toDataURL();
      doc['content'].push(
        " ",
        {text: "AbSplice tissue prediction", style: "table_subtitle", tocItem: true},
        "The scores represent the probability that a given variant causes aberrant splicing in a given tissue. AbSplice thresholds are defined as 0.01 (low), 0.05 (intermediate), and 0.2 (high).",
        {image: absplice_bar_chart, width: 500, alignment: 'center'}
      );
    }
    if ($('#igv_div').length && igv.browser) {
      // var igv_svg = igv.browser.toSVG();
      doc['content'].push(
        " ",
        {text: "SpliceAI-visual IGV view", style: "table_subtitle", tocItem: true},
        " ",
        " ",
        {svg: igv.browser.toSVG(), width: 500, alignment: 'center'},
        " ",
      );
    }
    if ($('#missense_table').length) {
      doc['content'].push(
        " ",
        {text: "Missense predictions", style: "table_title"},
        " ",
      );
      if ($('#missense_radar').width() > 0) {
        // attempt to transform radars into pdf
        var missense_radar_image = document.querySelector('#missense_radar').toDataURL();
        doc['content'].push(
          " ",
          {text: "Missense radar", style: "table_subtitle", tocItem: true},
          "Values are normalised (0-1), 0 being the less damaging and 1 the most for each predictor.",
          {image: missense_radar_image, width: 350, alignment: 'center'}
        );
      }
      doc = convert_dt(config, "missense_table", "Missense predictions", "table_subtitle", doc);
    }
    if ($('#dbmts_table').length) {
      doc = convert_dt(config, "dbmts_table", "dbMTS results", "table_title", doc);
    }
    if ($('#morfee_table').length) {
      doc = convert_dt(config, "morfee_table", "MORFEE results", "table_title", doc);
    }
    if ($('#episignature_table').length) {
      doc = convert_dt(config, "episignature_table", "Epigenetic signature", "table_title", doc);
    }
    if ($('#class_table').length) {
      doc = convert_dt(config, "class_table", "Classification history", "table_title", doc);
    }
    // pubmed
    if ($('#hidden_pubmed_results').length > 0) {
      const articles = $('#hidden_pubmed_results').text().split(';');

      doc['content'].push(
        " ",
        {text: "Pubmed citations", style: "table_title", tocItem: true},
        " ",
        {
          ul: articles,
          pageBreak: 'after'
        }
      );
    }
    else {
      doc['content'].push(
        " ",
        {text: "Pubmed citations", style: "table_title"},
        " ",
        {text: "No Pubmed citations found using LitVar"}
      );
    }
    if ($('#admin_table').length) {
      doc = convert_dt(config, "admin_table", "Administrative data", "table_title", doc);
    }
    if ($('#resource_table').length) {
      doc = convert_dt(config, "resource_table", "Tools and versions", "table_title", doc);
    }


		//get formatted date to report access time
		// info.messageTop = formatDate();
    // optional places for additional data
		if (info.messageTop) {
			doc.content.unshift({
				text: info.messageTop,
				style: 'message',
				margin: [0, 0, 0, 12]
			});
		}

		if (info.messageBottom) {
			doc.content.push({
				text: info.messageBottom,
				style: 'message',
				margin: [0, 0, 0, 12]
			});
		}

		if (info.title) {
			doc.content.unshift({
				text: info.title,
				style: 'title',
				margin: [0, 0, 0, 12]
			});
		}

		if (config.customize) {
			config.customize(doc, config);
		}

    // console.log(doc.content )
    //pdfmake comes with datatables
		pdfMake.createPdf(doc).download($('#nm_var').text() + '.pdf');
	});
});
