$(document).ready(function(){
	// submit using the enter key in keyboard
	$('#new_variant').keydown(function (e) {
		//alert(e.which);
		if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
			$('#submit_btn').click();
			return false;
		} else {
			return true;
		}
	});
	if ($('#iso_form').length) {
		$('#alt_iso option[value=""]').prop('selected', true);
	}
	var wi = $(window).width();
	//alert(wi);
	if (wi < 600) {
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
	}
});
