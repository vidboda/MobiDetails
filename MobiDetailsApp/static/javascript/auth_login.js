function check_login_form() {	
	if ($("#email").val() != '' && $("#password").val() != '') {
		//alert($("#email").val());
		$('html').css('cursor', 'progress');
		$('#sub').css('cursor', 'progress');
		$('#sub').prop('disabled', true);
		return true;
	}
	else {
		return false;
	}
}