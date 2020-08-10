
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
function favourite(vf_id, fav_url, csrf_token) {
	// send header for flask-wtf crsf security
	// alert($('#favour_span').attr('name'));
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });
	$.ajax({
		type: "POST",
		url: fav_url,
		data: {
			vf_id: vf_id, marker: $('#favour_span').attr('name')
		}
	})
	.done(function() {
		if ($('#favour_span').attr('name') === 'mark') {
			//$('#favour').removeClass('fa-star').addClass('fa-star-o');
			$('#favour').toggleClass('fa-star fa-star-o');
			$('#favour_span').attr('title', 'Unmark the variant');
			$('#favour_span').attr('name', 'unmark');
			// $('#favour_span').attr('onclick', "favourite('" + vf_id + "', 'unmark');");
			$('#favour_star').show();
		}
		else {
			//$('#favour').removeClass('fa-star-o').addClass('fa-star');
			$('#favour').toggleClass('fa-star-o fa-star');
			$('#favour_span').attr('title', 'Mark the variant');
			$('#favour_span').attr('name', 'mark');
			// $('#favour_span').attr('onclick', "favourite('" + vf_id + "', 'mark');");
			$('#favour_star').hide();
		}
		
	});
}
function litvar(litvar_url, csrf_token) {
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
		$("#litvar_data").replaceWith('<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">requesting LitVar for Pubmed IDs requires a dbSNP identifier</div>');
	}
}
function lovd(lovd_url, csrf_token) {
	// ajax for LOVD
	//var params = $.param(
	//	{
	//		genome: $('#genome_19').text(),
	//		chrom: $('#chrom_19').text(),
	//		pos: $('#pos_19').text(),
	//		g_name: $('#hg19_g_name').text(),
	//		c_name: $('#c_name').text()
	//	}
	//);
	// alert(params);
	//var html_comment = $("#acmg_comment").val().replace(/\r\n|\r|\n/g,"<br />");
	//var c_name_encoded = encodeURIComponent($('#c_name').text());
	// var c_name_encoded = $('#c_name').text().replace(/>/g,"%3E");
	// var g_name_encoded = $('#hg19_g_name').text().replace(/>/g,"%3E");
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
			genome: $('#genome_19').text(), chrom: $('#chrom_19').text(), pos: $('#pos_19').text(), g_name: $('#hg19_g_name').text(), c_name: $('#c_name').text()
		}
		/*data: {
			params
		}*/
	})
	.done(function(html) {
		$("#lovd_data").replaceWith(html);
        $("#lovd_feature").css("vertical-align", "middle");
        $("#lovd_description").css("vertical-align", "middle");
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
				genome: $('#genome_19').text(), chrom: $('#chrom_19').text(), pos: $('#pos_19').text(), ref: $('#ref_19').text(), alt: $('#alt_19').text()
			}
		})
		.done(function(html) {
			$("#intervar_data").replaceWith(html);
		});
	}
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
		//if (tr_html !== 'notok') {
			var re = /already_classified/;
			if ($("#" + mobiuser_id + "-" + acmg + "-" + variant_id).length > 0 ) {
				if (!re.test(tr_html)) {
					$("#" + mobiuser_id + "-" + acmg + "-" + variant_id).hide();
				}
				else {					
					$("#" + mobiuser_id + "-" + acmg + "-" + variant_id).css('font-weight', 'bold');
				}
            }
			if ($("#already_classified").length > 0) {
                $("#already_classified").remove();
            }
            $("#class_table>tbody:last").append(unescape(tr_html));
			$("#" + mobiuser_id + "-" + acmg + "-" + variant_id).css('font-weight', 'bold');
			$("#acmg_comment").val('');
			if ($("#no_class").length > 0) {
                $("#no_class").hide();
            }
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
            $("#"+mobiuser_id+"-"+acmg_class+"-"+variant_id).remove();
        }
		else {
			$("#message_return").html(return_code);
		}
	});
}


function send_var_message(url, csrf_token) {
    // ajax to send email
	var html_message = $("#message_body").val().replace(/\r\n|\r|\n/g,"<br />");
    // html_message = html_message.replace(/'/g,"\'");
    // html_message = html_message.replace(/"/g,'\"');
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


function myAccFunc(acc_id, icon_id) {
	// adapted from https://www.w3schools.com/w3css/tryit.asp?filename=tryw3css_sidebar_accordion
	// should be rewritten in jquery for consistency
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


// https://www.chartjs.org/docs/latest/general/responsive.html#important-note
function beforePrintHandler () {
    for (var id in Chart.instances) {
        Chart.instances[id].resize();
    }
}


$(document).ready(function() {
    // hide sidebar on small screen
	// if ($('#smart_menu').length) {		
	if ($(window).width() < 600) {
		$('#page_menu').remove();
        // hide left menu items
		myAccFunc('hg19_acc', 'hg19_icon');
		myAccFunc('hg38_acc', 'hg38_icon');
		$('#smart_menu').hide();
		$('#openNav').css('visibility', 'visible');
		$('#global_content').animate({marginLeft: '0%'});
		$('#mobile_var_name').show();
		$('#defgen_hg19').remove();
		$('#defgen_hg38').remove();
		
	}
    else if($(window).width() < 1300) {
        if ($('#login_name').length) {$('#login_name').remove();}
    }
    
    // transform all tables as datatables
	$('.w3-table').DataTable({
		responsive: true,
		dom: 't',
		"order": [],
		//scrollY: 600,
		buttons: [
				'copy', 'excel', 'pdf'
		]
	});
	
	// adapted from https://sharepoint.stackexchange.com/questions/234464/datatables-plugin-print-multiple-tables-on-one-page
	// export multiple tables in one single pdf
	$('#ExportPdf').click(function() {
	
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
			title: "*"
		};
		var tables = ["nomenclature_table", "position_table", "population_table",  "prediction_table"];
		if ($('#splicing_table').length > 0) {
			tables.push("splicing_table");
		}
		tables.push("maxent5ss_table");
		tables.push("maxent3ss_table");
		if ($('#missense_table').length > 0) {
			tables.push("missense_table");
		}
		tables.push("class_table");
		tables.push("admin_table");
		tables.push("resource_table");
		// var tables = ["nomenclature_table", "position_table", "population_table", "splicing_table", "missense_table", "prediction_table", "admin_table"];
		var tablesConverted = {};
		for (var k = 0; k < tables.length; k++) {
			var dt = $('#' + tables[k]).DataTable();
			var data = dt.buttons.exportData(config.exportOptions);
			var info = dt.buttons.exportInfo(config);
			// alert(tables[k]);
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
					return {
						text: typeof d === 'string' ? d : d + '',
						style: i % 2 ? 'tableBodyEven' : 'tableBodyOdd'
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
	
			tablesConverted[tables[k]] = rows;
        }
	
	
		var doc = {
			pageSize: config.pageSize,
			pageOrientation: config.orientation,
			content: [
				"Data for " + tables[0],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[0]]
					},
					layout: 'noBorders'
				},
				" ",
				"Data for " + tables[1],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[1]]
					},
					layout: 'noBorders'
				},
				" ",
				"Data for " + tables[2],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[2]]
					},
					layout: 'noBorders'
				},
				" ",
				"Data for " + tables[3],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[3]]
					},
					layout: 'noBorders'
				},
				" ",
				"Data for " + tables[4],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[4]]
					},
					layout: 'noBorders'
				},
				" ",
				"Data for " + tables[5],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[5]]
					},
					layout: 'noBorders'
				},
				"Data for " + tables[6],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[6]]
					},
					layout: 'noBorders'
				},
                "Data for " + tables[7],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[7]]
					},
					layout: 'noBorders'
				},
                "Data for " + tables[8],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[8]]
					},
					layout: 'noBorders'
				},
			//images: [],			
			//	" ",
			//	"Data for " + tables[5],
			//	" ", {
			//		table: {
			//			headerRows: 1,
			//			body: tablesConverted[tables[5]]
			//		},
			//		layout: 'noBorders'
			//	},
			//	" ",
			//	"Data for " + tables[6],
			//	" ", {
			//		table: {
			//			headerRows: 1,
			//			body: tablesConverted[tables[6]]
			//		},
			//		layout: 'noBorders'
			//	},
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
				tableFooter: {
					bold: true,
					fontSize: 11,
					color: 'white',
					fillColor: '#2d4154'
				},
				title: {
					alignment: 'center',
					fontSize: 15
				},
				message: {}
			},
			defaultStyle: {
				fontSize: 10
			}
		};
		if ($('#splicing_table').length > 0) {
			doc['content'].push(
				" ",
				"Data for " + tables[9],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[9]]
					},
					layout: 'noBorders'
				}
			);
		}
		if ($('#missense_table').length > 0) {
			doc['content'].push(
				" ",
				"Data for " + tables[10],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[10]]
					},
					layout: 'noBorders'
				}
			);
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
		
		//get formatted date to report access time
		info.messageTop = formatDate();
		
		//if ($('#missense_radar').length) {
		////	//attempt to transform chart.js canvas into pdf
		////	info.messageBottom = document.getElementById('missense_radar').toDataURL();
		//	var canvas = document.querySelector('#missense_radar');
		//	//doc.content.push({
		//	//	image:'data:image/jpeg;base64,' + canvas.toDataURL("image/jpeg", 1.0)
		//	//});
		//	//creates image
		//	//var canvasImg = canvas.toDataURL("image/jpeg", 1.0);
		//	//creates PDF from img
		//	//var doc_chart = new jsPDF('landscape');
		//	//doc.setFontSize(20);
		//	//doc.text(15, 15, "Cool Chart");
		//	//doc_chart.addImage(canvasImg, 'JPEG', 10, 10, 280, 150 );
		//	//info.radarImg = canvasImg
		//}
//        if ($('#segment_drawing').length) {
////			//attempt to transform exon/intron canvas into pdf
//            //info.messageBottom = $('#segment_drawing').toDataURL();
//			var canvas = document.querySelector('#segment_drawing');
//			doc.content.push({
//				image:'data:image/jpeg;base64,' + canvas.toDataURL("image/jpeg", 1.0)
//			});
////		//	//creates image
////		//	//var canvasImg = canvas.toDataURL("image/jpeg", 1.0);
////		//	//creates PDF from img
////		//	//var doc_chart = new jsPDF('landscape');
////		//	//doc.setFontSize(20);
////		//	//doc.text(15, 15, "Cool Chart");
////		//	//doc_chart.addImage(canvasImg, 'JPEG', 10, 10, 280, 150 );
////		//	//info.radarImg = canvasImg
//		}
		
		if (info.messageTop) {
			doc.content.unshift({
				text: info.messageTop,
				style: 'message',
				margin: [0, 0, 0, 12]
			});
		}
		//if (info.radarImg) {
		//	doc.content.push({
		//		image:'data:image/jpeg;base64,' + info.radarImg
		//	});
		//	//doc.images.push({
		//	//	radarImg: 'data:image/jpeg;base64,' + info.radarImg
		//	//});
		//}		
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
		pdfMake.createPdf(doc).download($('#nm_var').text() + '.pdf');
		//'{{ variant_features.gene_name[1] }}.{{ variant_features.nm_version }}_{{ variant_features.c_name }}.pdf'
	});
});