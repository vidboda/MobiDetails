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
	$('.w3-table').DataTable({
		responsive: true,
		dom: 'Bft',
		"order": [],
		//scrollY: 600,
		"pageLength": 50,
		buttons: [
			'copy', 'excel', 'pdf'
		]
	});
});
