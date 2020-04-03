$(document).ready(function(){
	$('.w3-table').DataTable({
		responsive: true,
		lengthMenu: [ [50, 100, 200, -1], [50, 100, 200, "All"] ],
		dom: 'lfrtBip',
		scrollY: 600,
		"order": [[ 3, 'asc' ], [ 0, 'asc' ]],
		buttons: [
			'copy', 'excel', 'pdf'
		]
	});
    var wi = $(window).width();
	//alert(wi);
	if (wi < 600) {
        $('td').addClass('w3-left-align');
    }
});

