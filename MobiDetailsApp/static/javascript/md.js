function accord(id) {
	$('#'+id).fadeToggle("slow");
}
function w3_open() {
	$('#smart_menu').width('15%');
	$('#smart_menu').show();
	var wi = $(window).width();
	if (wi < 600) {
		$('#global_content').animate({marginLeft: '35%'});
		$('#smart_menu').width('35%');
		$('#smart_menu').children().toggleClass('w3-large', 'w3-small');
		$('#smart_menu').children().toggleClass('w3-xxlarge', 'w3-small');
	}
	else {
		$('#global_content').animate({marginLeft: '15%'});
	}
	$('#openNav').css('visibility', 'hidden');
  //document.getElementById('smart_menu').style.width = '15%';
	//document.getElementById('global_content').style.marginLeft = '15%';
  //document.getElementById('smart_menu').style.display = 'block';
	//document.getElementById('openNav').style.visibility = 'hidden';
}
function w3_close() {
	$('#smart_menu').hide();
	$('#global_content').animate({marginLeft: '0%'});
	$('#openNav').css('visibility', 'visible');
	//document.getElementById('smart_menu').style.display = 'none';
	//document.getElementById('openNav').style.visibility = 'visible';
	//document.getElementById('global_content').style.marginLeft = '0%';
}
$(document).ready(function(){
	//reduce icon size on small screens
	var wi = $(window).width();
	//alert(wi);
	if (wi < 400) {
		$('i').toggleClass('w3-xxlarge w3-small');
		$('#engine').toggleClass('w3-large w3-small');
		$('#submit_a').toggleClass('w3-large w3-small');
		$('#logout').removeClass('w3-right');
		$('#myprofile').removeClass('w3-right');
		if ($('#variant_name').length) {
			$('#variant_name').hide();
		}
		if ($('#login_name').length) {
			$('#login_name').hide();
		}
		//if ($('#smart_menu').length) {
		//	$('#smart_menu').hide();
		//}
	}
	else if (wi <= 600) {
		$('i').toggleClass('w3-xxlarge w3-large');
		$('#engine').toggleClass('w3-large w3-small');
		$('#submit_a').toggleClass('w3-large w3-small');
		$('#logout').removeClass('w3-right');
		$('#myprofile').removeClass('w3-right');
		if ($('#variant_name').length) {
			$('#variant_name').hide();
		}
		if ($('#login_name').length) {
			$('#login_name').hide();
		}
		//if ($('#smart_menu').length) {
		//	$('#smart_menu').hide();
		//}
	}
	else if (wi <= 900) {
		$('i').toggleClass('w3-xxlarge w3-xlarge');
		if ($('#variant_name').length) {
			$('#variant_name').toggleClass('w3-xlarge w3-large');
		}
		if ($('#login_name').length) {
			$('#login_name').toggleClass('w3-xlarge w3-large');
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