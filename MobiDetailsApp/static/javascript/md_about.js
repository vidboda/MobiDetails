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
});