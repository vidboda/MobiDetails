function accord(id) {
	if ($('#'+id).css('display') == 'block') {$('#'+id).hide();}
	else {$('#'+id).show();}
}
function w3_open() {
  document.getElementById("smart_menu").style.width = '15%';
  document.getElementById("smart_menu").style.display = 'block';
	document.getElementById("openNav").style.visibility = 'hidden';
}
function w3_close() {
	document.getElementById("smart_menu").style.display = 'none';
	document.getElementById("openNav").style.visibility = 'visible';
}
$(document).ready(function(){
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