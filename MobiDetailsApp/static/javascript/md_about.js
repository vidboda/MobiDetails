$(document).ready(function() {
	$('.w3-table').DataTable({
		responsive: true,
		dom: 'Bft',
		"order": [],
		//scrollY: 600,
		buttons: [
			'copy', 'excel', 'pdf'
		]
	});
});