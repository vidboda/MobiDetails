function accord(id) {
	if ($('#'+id).css('display') == 'block') {$('#'+id).hide();}
	else {$('#'+id).show();}
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