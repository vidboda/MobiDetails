function check_register_form() {
	if ($("#username").val() != '' && $("#password").val() != '' && $("#institute").val() != '' && $("#email").val() != '') {
		$('html').css('cursor', 'progress');
		$('#sub').css('cursor', 'progress');
		$('#sub').prop('disabled', true);
		return;
	}
	else {
		return false;
	}
}