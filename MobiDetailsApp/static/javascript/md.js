function accord(id) {
	$('#'+id).fadeToggle("slow");
}
function w3_open() {
	$('#smart_menu').width('15%');
	$('#smart_menu').show();	
	var wi = $(window).width();
	if (wi < 600) {
		$('#smart_menu').find('a').removeClass('w3-large').addClass('w3-small');
		$('#smart_menu').find('button').removeClass('w3-large').addClass('w3-small');
		$('#smart_menu').find('span').removeClass('w3-large').addClass('w3-small');
		$('#smart_menu').children().removeClass('w3-xxlarge').addClass('w3-small');
		$('#global_content').animate({marginLeft: '35%'});
		$('#smart_menu').width('35%');
	}
	else {
		$('#global_content').animate({marginLeft: '15%'});
	}
	$('#openNav').css('visibility', 'hidden');
}
function w3_close() {
	$('#smart_menu').hide();
	$('#global_content').animate({marginLeft: '0%'});
	$('#openNav').css('visibility', 'visible');
}
function copy_text(copy_id) {
	/* Get the text field */
  var copyText = document.getElementById(copy_id);
  /* Select the text field */
  copyText.select();
  copyText.setSelectionRange(0, 99999); /*For mobile devices*/
  /* Copy the text inside the text field */
  document.execCommand("copy");
  /* Alert the copied text */
  //alert("Copied the text: " + copyText.value);
}
function encode_params(input_id) {
    // function to encode params before forms submissions (e.g. because '>' are not encoded)
		var inter = $('#' + input_id).val();
		$('#' + input_id).css('visibility', 'hidden');
		$('html').css('cursor', 'progress');
		$('#' + input_id).val(encodeURIComponent(inter));
		// alert($('#' + input_id).val());
		return true;
}
$(document).ready(function(){
	//reduce icon size on small screens
	var wi = $(window).width();
	//alert(wi);
	if (wi < 400) {
		$('i').removeClass('w3-xxlarge').addClass('w3-small');
		$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-medium');
		$('span.w3-xlarge').removeClass('w3-xlarge').addClass('w3-medium');
		$('li.w3-xlarge').removeClass('w3-xlarge').addClass('w3-medium');
		$('.w3-modal').addClass('w3-small');
		$('#engine').removeClass('w3-large').addClass('w3-small');
		$('#submit_a').removeClass('w3-large').addClass('w3-small');
		$('#logout').removeClass('w3-right');
		$('#myprofile').removeClass('w3-right');
		if ($('#variant_name').length) {$('#variant_name').hide();}
		if ($('#about_menu').length) {$('#about_menu').hide();}
		if ($('#login_name').length) {$('#login_name').hide();}
		//if ($('#modify_class').length) {}
		if ($('#class_table').length) {$('#modify_class').hide();$('.fa-envelope-o').hide();}
		if ($('#login_form').length) {$('#login_form').css('width', '90%');}
		if ($('#register_form').length) {$('#register_form').css('width', '90%');}
	}
	else if (wi <= 600) {
		$('i').removeClass('w3-xxlarge').addClass('w3-large');
		$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-large');
		$('span.w3-xlarge').removeClass('w3-xlarge').addClass('w3-large');
		$('li.w3-xlarge').removeClass('w3-xlarge').addClass('w3-large');
		$('.w3-modal').addClass('w3-medium');
		$('#engine').removeClass('w3-large').addClass('w3-small');
		$('#submit_a').removeClass('w3-large').addClass('w3-small');
		$('#logout').removeClass('w3-right');
		$('#myprofile').removeClass('w3-right');
		if ($('#modify_class').length) {$('#modify_class').hide();}
		if ($('#variant_name').length) {$('#variant_name').hide();}
		if ($('#login_name').length) {$('#login_name').hide();}
		if ($('#about_menu').length) {$('#about_menu').hide();}
		if ($('#login_form').length) {$('#login_form').css('width', '80%');}
		if ($('#register_form').length) {$('#register_form').css('width', '80%');}
		//if ($('#smart_menu').length) {
		//	$('#smart_menu').hide();
		//}
	}
	else if (wi <= 900) {
		$('i').toggleClass('w3-xxlarge w3-xlarge');
		$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-xlarge');
		if ($('#login_form').length) {$('#login_form').css('width', '70%');}
		if ($('#register_form').length) {$('#register_form').css('width', '70%');}
		if ($('#variant_name').length) {
			$('#variant_name').removeClass('w3-xlarge').addClass('w3-large');
		}
		if ($('#login_name').length) {
			$('#login_name').removeClass('w3-xlarge').addClass('w3-large');
		}
	}
	// scroll nav-bar
	document.addEventListener('scroll', function(){
		var h = document.documentElement,
			b = document.body,
			st = 'scrollTop',
			sh = 'scrollHeight';
	
		var percent = (h[st]||b[st]) / ((h[sh]||b[sh]) - h.clientHeight) * 100;
		document.getElementById('scroll-bar').style.width = percent + '%';	
	});
});