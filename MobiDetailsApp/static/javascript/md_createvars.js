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
	// var c_name_encoded = $('#new_variant').val().replace(/>/g,"%3E");
	// encodeURIComponent($("#new_variant").val());
	$.ajax({
		type: "POST",
		url: create_url,
		data: {
			gene: $("#gene").val(), acc_no: $("#acc_no").val(), new_variant: $('#new_variant').val(), acc_version: $("#acc_version").val(), alt_iso: $("#alt_iso").val()
		}
	})
	.done(function(html) {
		$('#created_var').append(html);
		$('html').css('cursor', 'default');
		$('.w3-btn').css('cursor', 'default');
		$('#var_modal').hide();
	});
}