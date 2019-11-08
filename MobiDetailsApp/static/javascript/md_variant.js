
function defgen_export(genome, vf_id) {
	$.ajax({
		type: "POST",
		url: '/defgen',
		data: {
			vfid: vf_id, genome: genome
		}
	})
	.done(function(html) {
		$('#defgen_modal_' + genome).html(html);
		$('#defgen_modal_' + genome).show();
	});
}
function favourite(vf_id, marker) {
	$.ajax({
		type: "POST",
		url: '/favourite',
		data: {
			vf_id: vf_id, marker: marker
		}
	})
	.done(function() {
		if (marker === 'mark') {
			//$('#favour').removeClass('fa-star').addClass('fa-star-o');
			$('#favour').toggleClass('fa-star fa-star-o');
			$('#favour_span').attr('title', 'Unmark the variant');
			$('#favour_span').attr('onclick', "favourite('" + vf_id + "', 'unmark');");
			$('#favour_star').show();
		}
		else {
			//$('#favour').removeClass('fa-star-o').addClass('fa-star');
			$('#favour').toggleClass('fa-star-o fa-star');
			$('#favour_span').attr('title', 'Mark the variant');
			$('#favour_span').attr('onclick', "favourite('" + vf_id + "', 'mark');");
			$('#favour_star').hide();
		}
		
	});
}
function myAccFunc(acc_id, icon_id) {
	//adapted from https://www.w3schools.com/w3css/tryit.asp?filename=tryw3css_sidebar_accordion
	//should be rewritten in jquery for consistency
	var x = document.getElementById(acc_id);
	if (x.className.indexOf("w3-show") == -1) {
		//x.className += " w3-show";
		$('#' + acc_id).removeClass("w3-hide").addClass("w3-show");
		x.previousElementSibling.className += " w3-blue";
		$('#' + icon_id).removeClass("fa-caret-right").addClass("fa-caret-down");
	} else { 
		//x.className = x.className.replace(" w3-show", "");
		$('#' + acc_id).removeClass("w3-show").addClass("w3-hide");
		x.previousElementSibling.className = 
		x.previousElementSibling.className.replace(" w3-blue", "");
		$('#' + icon_id).removeClass("fa-caret-down").addClass("fa-caret-right");
	}
}
//https://www.chartjs.org/docs/latest/general/responsive.html#important-note
function beforePrintHandler () {
    for (var id in Chart.instances) {
        Chart.instances[id].resize();
    }
}
$(document).ready(function() {
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
	//ajax for litvar
	if ($('#dbsnp_id').text() !== '') {
		$.ajax({
			type: "POST",
			url: '/litVar',
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
	//ajax for intervar
	if ($('#dna_type').text() == 'substitution' && $('#segment_type').text() == 'exon') {
		$.ajax({
			type: "POST",
			url: '/intervar',
			data: {
				genome: $('#genome_19').text(), chrom: $('#chrom_19').text(), pos: $('#pos_19').text(), ref: $('#ref_19').text(), alt: $('#alt_19').text()
			}
		})
		.done(function(html) {
			$("#intervar_data").replaceWith(html);
		});
	}
	//ajax for LOVD
	$.ajax({
		type: "POST",
		url: '/lovd',
		data: {
			genome: $('#genome_19').text(), chrom: $('#chrom_19').text(), pos: $('#pos_19').text(), g_name: $('#hg19_g_name').text(), c_name: $('#c_name').text()
		}
	})
	.done(function(html) {
		$("#lovd_data").replaceWith(html);
	});
	//hide sidebar on small screen
	//if ($('#smart_menu').length) {		
	if ($(window).width() < 600) {
		$('#smart_menu').hide();
		$('#openNav').css('visibility', 'visible');
		$('#page_menu').hide();
		$('#global_content').animate({marginLeft: '0%'});
		$('#mobile_var_name').show();
		$('#defgen_hg19').hide();
		$('#defgen_hg38').hide();
		//hide left menu items
		myAccFunc('hg19_acc', 'hg19_icon');
		myAccFunc('hg38_acc', 'hg38_icon');
	}
	//adapted from https://sharepoint.stackexchange.com/questions/234464/datatables-plugin-print-multiple-tables-on-one-page
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
		if ($('#missense_table').length > 0) {
			tables.push("missense_table");
		}
		tables.push("admin_table");
		//var tables = ["nomenclature_table", "position_table", "population_table", "splicing_table", "missense_table", "prediction_table", "admin_table"];
		var tablesConverted = {};
		for (var k = 0; k < tables.length; k++) {
			var dt = $('#' + tables[k]).DataTable();
			var data = dt.buttons.exportData(config.exportOptions);
			var info = dt.buttons.exportInfo(config);
			//alert(tables[k]);
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
			],
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
			//],
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
				"Data for " + tables[5],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[5]]
					},
					layout: 'noBorders'
				}
			);
		}
		if ($('#missense_table').length > 0) {
			doc['content'].push(
				" ",
				"Data for " + tables[6],
				" ", {
					table: {
						headerRows: 1,
						body: tablesConverted[tables[6]]
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
			js_date = "MobiDetails accessed " + d.toLocaleDateString();
			js_time = " - " + h + ":" + m + ":" + s;
			return js_date + js_time;// + "-" h + ":" + m + ":" + s;
		} 
		
		//get formatted date to report access time
		info.messageTop = formatDate();
		
		if ($('#missense_radar').length) {
		//	//attempt to transform chart.js canvas into pdf
		//	info.messageBottom = document.getElementById('missense_radar').toDataURL();
			var canvas = document.querySelector('#missense_radar');
			//doc.content.push({
			//	image:'data:image/jpeg;base64,' + canvas.toDataURL("image/jpeg", 1.0)
			//});
			//creates image
			//var canvasImg = canvas.toDataURL("image/jpeg", 1.0);
			//creates PDF from img
			//var doc_chart = new jsPDF('landscape');
			//doc.setFontSize(20);
			//doc.text(15, 15, "Cool Chart");
			//doc_chart.addImage(canvasImg, 'JPEG', 10, 10, 280, 150 );
			//info.radarImg = canvasImg
		}
		
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