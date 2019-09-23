
function defgen_export(genome, vf_id) {
	$.ajax({
		type: "POST",
		url: '/defgen',
		data: {
			vfid: vf_id,
			genome: genome
		}
	})
		.done(function(html) {
		$('#defgen_modal_' + genome).html(html);
		$('#defgen_modal_' + genome).show();
	});
}


$(document).ready(function() {
	$('.w3-table').DataTable({
		responsive: true,
		dom: 'ft',
		"order": [],
		//scrollY: 600,
		buttons: [
				'copy', 'excel', 'pdf'
		]
	});
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
	//$('#defgen_btn').click(function(){	
	//alert($('#dbsnp_id').text());
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

		var tables = ["nomenclature_table", "position_table", "population_table", "splicing_table", "missense_table"];
		var tablesConverted = {};
		for (var k = 0; k < tables.length; k++) {
			var dt = $('#' + tables[k]).DataTable();
			var data = dt.buttons.exportData(config.exportOptions);
			var info = dt.buttons.exportInfo(config);

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
		pdfMake.createPdf(doc).download($('#nm_var').text());
		//'{{ variant_features.gene_name[1] }}.{{ variant_features.nm_version }}_{{ variant_features.c_name }}.pdf'
	});
});