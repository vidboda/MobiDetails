function create_var(create_url) {
	$("#error_name").empty();
	$('html').css('cursor', 'progress');
	$('.w3-btn').css('cursor', 'progress');
	//alert($("#new_variant").val());
	if ($("#new_variant").val() == '' || $("#new_variant").val() == 'c.') {
		$("#error_name").append('<span>Please enter a variant name</span>');
		$('html').css('cursor', 'default');
		$('.w3-btn').css('cursor', 'default');
		$("#new_variant").focus();
		return false;
	}
	var c_name_encoded = $('#new_variant').val().replace(/>/g,"%3E");
	// encodeURIComponent($("#new_variant").val());
	$.ajax({
		type: "POST",
		url: create_url,
		data: {
			gene: $("#gene").val(), acc_no: $("#acc_no").val(), new_variant: c_name_encoded, acc_version: $("#acc_version").val(), alt_iso: $("#alt_iso").val()
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