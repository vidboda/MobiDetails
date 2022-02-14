function create_var(create_url, csrf_token) {
	$("#error_name").empty();
	$('html').css('cursor', 'progress');
	$('.w3-btn').css('cursor', 'progress');
	$('#submit_btn').prop('disabled', true);
	//alert($("#new_variant").val());
	var new_variant = $('#new_variant').val().replace(/\s/g, "");
	if (new_variant == '' || new_variant == 'c.') {
	// if ($("#new_variant").val() == '' || $("#new_variant").val() == 'c.') {
		$("#error_name").append('<span>Please enter a variant name</span>');
		$('html').css('cursor', 'default');
		$('.w3-btn').css('cursor', 'default');
		$("#new_variant").focus();
		return false;
	}
	// var c_name_encoded = $('#new_variant').val().replace(/>/g,"%3E");
	// encodeURIComponent($("#new_variant").val());
	//send header for flask-wtf crsf security
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });
	$.ajax({
		type: "POST",
		url: create_url,
		data: {
			gene: $("#gene").val(), acc_no: $("#acc_no").val(), new_variant: new_variant, alt_iso: $("#alt_iso").val()
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

// https://www.w3schools.com/howto/howto_css_loader.asp
function gene_loader() {
	$('#loader').show();
	$('.tab_content').hide();
}
