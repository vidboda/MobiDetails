function check_login_form() {
	if ($("#email").val() != '' && $("#password").val() != '') {
		$('html').css('cursor', 'progress');
		$('#sub').css('cursor', 'progress');
		$('#sub').attr('disabled', 'disabled');
		return;
	}
	else {
		return false;
	}
}