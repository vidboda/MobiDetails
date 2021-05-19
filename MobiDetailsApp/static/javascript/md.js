// https://www.w3schools.com/howto/howto_css_loader.asp
function show_loader() {
	$('#loader').show();
	$('#content').hide();
	if ($('header').length) {$('header').hide();}
}

document.onreadystatechange = function() {
  if (document.readyState !== "complete") {
		$('#loader').show();
		$('#content').hide();
  } else {
		$('#loader').hide();
		$('#content').show();
  }
};

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
	else if (wi < 900) {
		$('#smart_menu').find('a').removeClass('w3-large').addClass('w3-medium');
		$('#smart_menu').find('button').removeClass('w3-large').addClass('w3-medium');
		$('#smart_menu').find('span').removeClass('w3-large').addClass('w3-medium');
		$('#smart_menu').children().removeClass('w3-xxlarge').addClass('w3-medium');
		$('#global_content').animate({marginLeft: '25%'});
		$('#smart_menu').width('25%');
	}
	else if (wi < 1300) {
		$('#smart_menu').find('a').removeClass('w3-large').addClass('w3-medium');
		$('#smart_menu').find('button').removeClass('w3-large').addClass('w3-medium');
		$('#smart_menu').find('span').removeClass('w3-large').addClass('w3-medium');
		$('#smart_menu').children().removeClass('w3-xxlarge').addClass('w3-medium');
		$('#global_content').animate({marginLeft: '15%'});
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
	// adpated from https://www.w3schools.com/howto/howto_js_copy_clipboard.asp
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
function hide_params() {
    // function to hide params when a form is sent (long response time e.g. register)
		$('input').css('visibility', 'hidden');
		$('select').css('visibility', 'hidden');
		$('html').css('cursor', 'progress');
		return true;
}
//function encode_vars(id) {
//    // function to specifically encode params before forms submissions ( because '>' are not encoded)
//		// and encodeURIComponent triggers mod_security mutliple encodings
//		// DEPRECATED 04/2020
//		var inter = $('#' + id).val();
//		$('#' + id).val(inter.replace(/>/g,"%3E"));
//		return true;
//}
//function encode_params(input_id) {
//    // function to encode params before forms submissions (e.g. because '>' are not encoded)
//		// DEPRECATED 04/2020
//		var inter = $('#' + input_id).val();
//		//$('#' + input_id).css('visibility', 'hidden');
//		//$('html').css('cursor', 'progress');
//		$('#' + input_id).val(encodeURIComponent(inter));
//		// alert($('#' + input_id).val());
//		return true;
//}
// used in md.variant and auth.profile.html
function favourite(vf_id, fav_url, csrf_token) {
	// send header for flask-wtf crsf security
  $.ajaxSetup({
      beforeSend: function(xhr, settings) {
          if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrf_token);
          }
      }
  });
	// call form variant page
	var favour_span_id;
	var favour_id;
	if ($('#favour_span').length) {
		favour_span_id = 'favour_span';
		favour_id = 'favour';
	}
	else {
		//call form profile page
		favour_span_id = 'favour_span_' + vf_id;
		favour_id = 'favour_' + vf_id;
	}
	$.ajax({
		type: "POST",
		url: fav_url,
		data: {
			vf_id: vf_id, marker: $('#' + favour_span_id).attr('name')
		}
	})
	.done(function() {
		if ($('#' + favour_span_id).attr('name') === 'mark') {
			//$('#favour').removeClass('fa-star').addClass('fa-star-o');
			$('#' + favour_id).toggleClass('fa-star fa-star-o');
			$('#' + favour_span_id).attr('title', 'Unmark the variant');
			$('#' + favour_span_id).attr('name', 'unmark');
			if ($('#favour_span').length) {
				// call from variant page
				$('#favour_star').show();
			}
			else {
				// $('#favourite_ul').append('<li id="favourite_li_' + vf_id + '" class="w3-padding-large w3-large w3-light-grey w3-hover-blue var_li" onclick="window.open(\'' + encodeURIComponent($("#md_variant_url_" + vf_id).text()) + '\')" title="Visit the variant page"><span><em>' + encodeURIComponent($("#gene_" + vf_id).text()) + '</em>:c.' + encodeURIComponent($("#c_name_" + vf_id).text()) + ' - p.(' + encodeURIComponent($("#p_name_" + vf_id).text()) + ')</span><span class="w3-right"><i class="fa fa-star w3-xxlarge"></i></span></li>');
				$('#favourite_ul').append('<li id="favourite_li_' + vf_id + '" class="w3-padding-large w3-large w3-light-grey w3-hover-blue var_li" onclick="window.open(\'' + $("#md_variant_url_" + vf_id).text() + '\')" title="Visit the variant page"><span><em>' + $("#gene_" + vf_id).text() + '</em>:c.' + $("#c_name_" + vf_id).text() + ' - p.(' + $("#p_name_" + vf_id).text() + ')</span><span class="w3-right"><i class="fa fa-star w3-xxlarge"></i></span></li>');
				$('#favourite_vars').show();
				$('#variant_list').show();
				if ($('#num_favourite').length) {
					var num_fav = parseInt($('#num_favourite').text()) + 1;
					$('#num_favourite').text(num_fav);
				}
				else {
					$('#favourite_title').html('Toggle your <span id="num_favourite">1</span> favourite variant');
				}
			}
		}
		else {
			//$('#favour').removeClass('fa-star-o').addClass('fa-star');
			$('#' + favour_id).toggleClass('fa-star-o fa-star');
			$('#' + favour_span_id).attr('title', 'Mark the variant');
			$('#' + favour_span_id).attr('name', 'mark');
			// $('#favour_span').attr('onclick', "favourite('" + vf_id + "', 'mark');");
			if ($('#favour_span').length) {
				$('#favour_star').hide();
			}
			else {
				$('#favourite_li_'+ vf_id).remove();
				var num_fav = parseInt($('#num_favourite').text()) - 1;
				if(num_fav > 0) {
					$('#num_favourite').text(num_fav);
				}
				else {
					$('#favourite_title').text('You have no favourite variants yet.');
				}
			}
		}

	});
}
$(document).ready(function(){
	// $('#loader').hide();
	// $('#content').show();
	// change z-index for menus
	$('#mdNavBar').mouseenter(
		function () {
			if ($('#about_menu').length) {$('#about_menu').css('z-index', 1111);}
			if ($('#page_menu').length) {$('#page_menu').css('z-index', 1111);}
			if ($('#smart_menu').length) {$('#smart_menu').css('z-index', 1111);}
    }
	);
	$('#mdNavBar').mouseleave(
		function () {
			if ($('#about_menu').length) {$('#about_menu').css('z-index', 1300);}
			if ($('#page_menu').length) {$('#page_menu').css('z-index', 1300);}
			if ($('#smart_menu').length) {$('#smart_menu').css('z-index', 1300);}
    }
	);

	// reduce icon size on small screens
	var wi = $(window).width();
	// alert(wi);
	if (wi < 400) {
		$('i').removeClass('w3-xxlarge').addClass('w3-small');
		$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-medium');
		$('span.w3-xlarge').removeClass('w3-xlarge').addClass('w3-medium');
		$('li.w3-xlarge').removeClass('w3-xlarge').addClass('w3-medium');
		$('.w3-modal').addClass('w3-small');
		$('#engine').removeClass('w3-xlarge').addClass('w3-small');
		$('#submit_a').removeClass('w3-large').addClass('w3-small');
		$('#logout').removeClass('w3-right');
		$('#myprofile').removeClass('w3-right');
		if ($('#variant_name').length) {$('#variant_name').remove();}
		if ($('#about_menu').length) {$('#about_menu').remove();}
		if ($('#login_name').length) {$('#login_name').remove();}
		// if ($('#modify_class').length) {}
		if ($('#class_table').length) {$('#modify_class').remove();$('.fa-envelope-o').remove();}
		if ($('#login_form').length) {$('#login_form').css('width', '90%');}
		if ($('#register_form').length) {$('#register_form').css('width', '90%');}
	}
	else if (wi <= 600) {
		$('i').removeClass('w3-xxlarge').addClass('w3-large');
		$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-large');
		$('span.w3-xlarge').removeClass('w3-xlarge').addClass('w3-large');
		$('li.w3-xlarge').removeClass('w3-xlarge').addClass('w3-large');
		$('.w3-modal').addClass('w3-medium');
		$('#engine').removeClass('w3-xlarge').addClass('w3-small');
		$('#engine').css('width', '150px');
		$('#submit_a').removeClass('w3-large').addClass('w3-small');
		$('#logout').removeClass('w3-right');
		$('#myprofile').removeClass('w3-right');
		if ($('#modify_class').length) {$('#modify_class').remove();}
		if ($('#variant_name').length) {$('#variant_name').remove();}
		if ($('#login_name').length) {$('#login_name').remove();}
		if ($('#about_menu').length) {$('#about_menu').remove();}
		if ($('#login_form').length) {$('#login_form').css('width', '80%');}
		if ($('#register_form').length) {$('#register_form').css('width', '80%');}
		//if ($('#smart_menu').length) {
		//	$('#smart_menu').hide();
		//}
	}
	else if (wi <= 900) {
		$('i').toggleClass('w3-xxlarge w3-large');
		$('span.w3-xxlarge').removeClass('w3-xxlarge').addClass('w3-xlarge');
		$('input.w3-xlarge').removeClass('w3-xlarge').addClass('w3-large');
		$('#engine').css('width', '150px');
		if ($('#login_form').length) {$('#login_form').css('width', '70%');}
		if ($('#register_form').length) {$('#register_form').css('width', '70%');}
		if ($('#variant_name').length) {
			$('#variant_name').removeClass('w3-xlarge').addClass('w3-large');
		}
		if ($('#login_name').length) {$('#login_name').remove();}
		if ($('#page_menu').length) {$('#page_menu').remove();}
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
