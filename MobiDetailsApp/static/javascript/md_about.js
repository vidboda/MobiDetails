$(document).ready(function() {
	// reduce txt size on small screens
	//var wi = $(window).width();
	// alert(wi);
	//if (wi < 400) {
	//
	//else if (wi <= 600) {
	//	$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-medium');
	//}
	//else if (wi <= 900) {
	//	$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-xlarge');
	//}
	$('#reference_table').DataTable({
		responsive: true,
		dom: 'Bft',
		"order": [],
		//scrollY: 600,
		"pageLength": 50,
		buttons: [
			'copy', 'excel', 'pdf'
		]
	});
		$('#download_table').DataTable({
		responsive: true,
		searching: false,
		paging: false,
		ordering: false,
		// dom: 'Bft',
		//scrollY: 600,
		"pageLength": 5,
	});
});
