$(document).ready(function(){
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