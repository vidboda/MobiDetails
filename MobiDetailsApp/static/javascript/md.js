function accord(id) {
	$('#'+id).fadeToggle("slow");
	//if ($('#'+id).css('display') == 'block') {$('#'+id).hide();}
	//else {$('#'+id).show();}
}
function w3_open() {
  document.getElementById('smart_menu').style.width = '15%';
	document.getElementById('global_content').style.marginLeft = '15%';
  document.getElementById('smart_menu').style.display = 'block';
	document.getElementById('openNav').style.visibility = 'hidden';
}
function w3_close() {
	document.getElementById('smart_menu').style.display = 'none';
	document.getElementById('openNav').style.visibility = 'visible';
	document.getElementById('global_content').style.marginLeft = '0%';
}
$(document).ready(function(){
	//reduce icon size on small screens
	if ($('#smart_menu').length) {		
		if ($(window).width() < 400) {
			$('i').toggleClass('w3-xxlarge w3-large');
			$('#variant_name').toggleClass('w3-xlarge w3-small');
			$('#engine').toggleClass('w3-large w3-small');
			$('#submit_a').toggleClass('w3-large w3-small');
		}
		else if ($(window).width() <= 900) {
			$('i').toggleClass('w3-xxlarge w3-xlarge');
			$('#variant_name').toggleClass('w3-xlarge w3-large');
		}
		//alert($(window).width());
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