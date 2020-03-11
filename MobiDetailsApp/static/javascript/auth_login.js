function check_login_form() {	
	if ($("#email").val() != '' && $("#password").val() != '') {
		//alert($("#email").val());
		$('html').css('cursor', 'progress');
		$('#sub').css('cursor', 'progress');
		$('#sub').attr('disabled', 'disabled');
		return true;
	}
	else {
		return false;
	}
}