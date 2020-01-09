$(document).ready(function() {
	$('#gene_table').DataTable({
		responsive: true,
		lengthMenu: [ [50, 100, 200, -1], [50, 100, 200, "All"] ],
		dom: 'lfrtBip',
		scrollY: 600,
		"order": [],
		buttons: [
			'copy', 'excel', 'pdf'
		]
	});
	$('#waiting_wheel').hide();
	$('#gene_table').show();
});