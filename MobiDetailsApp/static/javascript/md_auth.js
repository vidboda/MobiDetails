function toggle_email_service(email_perf_url) {
    // ajax to modify prefs for email contacts
    $('html').css('cursor', 'progress');
    $.ajax({
		type: "POST",
		url: email_perf_url,
		data: {
			pref_value: $("#value_to_send").html()
		}
	})
	.done(function(return_value, html_error) {
		if (return_value == 'ok') {
            var txt = 'enabled';
            var label = 'Disable it';
            var value_to_send = 'f';
            if ($("#value_to_send").html() == 'f') {
                txt = 'disabled';
                label = 'Enable it';
                value_to_send = 't';
            }
            $("#value_to_send").html(value_to_send);
            $('#contact_btn').html(label);
            //$("#contact_box").prop( "checked", false);
            $('#contact_value').html(txt);
            //$('#contact_box_label').html(label);
            $('html').css('cursor', 'default');
        }
        else{
            //$("#contact_box").prop( "checked", false);
            $('#error_messages').html(html_error);
            $('html').css('cursor', 'default');
        }
        
	});
}