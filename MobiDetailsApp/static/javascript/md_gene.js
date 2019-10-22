function create_var() {
	$("#error_name").empty();
	$('html').css('cursor', 'progress');
	$('.w3-btn').css('cursor', 'progress');
	//alert($("#new_variant").val());
	if ($("#new_variant").val() == '' || $("#new_variant").val() == 'c.') {
		$("#error_name").append('<span>Please enter a variant name</span>');
		$('html').css('cursor', 'default');
		$('.w3-btn').css('cursor', 'default');
		return;
	}
	$.ajax({
		type: "POST",
		url: '/create',
		data: {
			gene: $("#gene").val(), acc_no: $("#acc_no").val(), new_variant: $("#new_variant").val(), acc_version: $("#acc_version").val(), alt_iso: $("#alt_iso").val()
		}
	})
	.done(function(html) {
		$('#created_var').append(html);
		$('html').css('cursor', 'default');
		$('.w3-btn').css('cursor', 'default');
		$('#var_modal').hide();
	});
}
function new_isoform() {
	$('#iso_form').fadeToggle(function (){
		if ($('#iso_form').css('display') == 'none') {
			$('#alt_iso option[value=""]').prop('selected', true);
		}
	});
}
$(document).ready(function(){
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