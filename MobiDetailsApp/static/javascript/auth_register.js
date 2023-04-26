function check_register_form() {
	if ($("#username").val() != '' && $("#password").val() != '' && $("#institute").val() != '' && $("#email").val() != '' && $("#country").val() != '' && $("#acad").val() != '') {
		/// check username at least 5 letters
		var re = /^[\w-]{5,100}$/;
		if (re.test($("#username").val()) === false) {show_error('Username should be at least 5 characters and contain only letters and numbers.');return false;}
		re = /(?!^[0-9]*$)(?!^[a-z]*$)(?!^[A-Z]*$)(?!^[a-zA-Z]*$)(?!^[a-z0-9]*$)(?!^[A-Z0-9]*$)^.{8,}$/;
		if (re.test($("#password").val()) === false) {show_error('Password should be at least 8 characters and mix at least letters (upper and lower case) and numbers.');return false;}
		re = /--/;
		if (re.test($("#country").val()) === true) {show_error('Country is required.');return false;}
		re = /^[\w\(\),;\.\s-]+$/;
		if (re.test($("#institute").val()) === false) {show_error('Invalid characters in the Institute field (please use letters, numbers and ,;.-()).');return false;}
		re = /^[a-zA-Z0-9\._%\+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
		if (re.test($("#email").val()) === false) {show_error('The email address does not look valid.');return false;}
		$('html').css('cursor', 'progress');
		$('#sub').css('cursor', 'progress');
		$('#sub').prop('disabled', true);
		$('.w3-button').css('cursor', 'progress');
		show_loader();
		return;
	}
	else {
		return false;
	}
}

function show_error(text_error) {
	$('#onsubmiterror').html('<p><strong>' + text_error + '</strong></p>')
}