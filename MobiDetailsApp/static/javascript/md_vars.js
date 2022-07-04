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
	$('.w3-table').DataTable({
		responsive: true,
		lengthMenu: [ [50, 100, 200, -1], [50, 100, 200, "All"] ],
		dom: 'lfrtBip',
		scrollY: 600,
		"order": [[ 3, 'asc' ], [ 0, 'asc' ]],
		buttons: [
			'copy', 'excel', 'pdf'
		]
	});
    var wi = $(window).width();
	//alert(wi);
	if (wi < 600) {
        $('td').addClass('w3-left-align');
    }
});
