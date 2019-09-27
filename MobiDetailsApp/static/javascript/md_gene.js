function create_var() {
	$('html').css('cursor', 'progress');
	$('.w3-btn').css('cursor', 'progress');
	$.ajax({
		type: "POST",
		url: '/create',
		data: {
			gene: $("#gene").val(), acc_no: $("#acc_no").val(), new_variant: $("#new_variant").val(), acc_version: $("#acc_version").val()
		}
	})
	.done(function(html) {
		$('#created_var').append(html);
		$('html').css('cursor', 'default');
		$('.w3-btn').css('cursor', 'default');
		$('#var_modal').hide();
	});
}