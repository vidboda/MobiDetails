function toggle_service(pref_url, csrf_token, caller) {
    // ajax to modify prefs for email contacts
    $('html').css('cursor', 'progress');
    $('#btn_' +  + caller).css('cursor', 'progress');
    // send header for flask-wtf crsf security
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
            // disable onclick
            $("span#btn_" + caller ).off("click");
        }
    });
    var value_id = $("#value_to_send_" + caller).html();
    $.ajax({
  		type: "POST",
  		url: pref_url,
  		data: {
  			pref_value: value_id, field: caller
  		}
  	})
  	.done(function(return_value, html_error) {
  		if (return_value == 'ok') {
              var txt = 'enabled';
              var label = '<i class="fa fa-toggle-on w3-xxlarge" style="vertical-align: middle;" title="Disable ' + title +'"></i>';
              var value_to_send = 'f';
              if (value_id == 'f') {
                  txt = 'disabled';
                  // label = 'Enable it';
                  var label = '<i class="fa fa-toggle-off w3-xxlarge" style="vertical-align: middle;" title="Enable ' + title +'"></i>';
                  value_to_send = 't';
              }
              var title = 'contact service';
              if (caller == 'lovd_export') {title = 'LOVD export';}
              else if (caller === 'clinvar_check') {
                title = 'ClinVar follow-up';
                if (value_id == 'f') {
                  // auto_add2clinvar_check became f in ajax as well
                  // we need to update the UI accordingly
                  $("#value_auto_add2clinvar_check").attr('class', 'w3-text-red');
                  $("#value_auto_add2clinvar_check").html(txt);
                  $("#value_to_send_auto_add2clinvar_check").html(value_to_send);
                  $("#btn_auto_add2clinvar_check").html(label);
                  // in addition the list is emptied
                  $("#num_clinvar_watched").text("0");
                  $("#clinvar_watched_list").html("");
                }
                $('#li_auto_add2clinvar_check').toggle();
              }
              else if (caller === 'auto_add2clinvar_check') {
                title = 'automatic ClinVar follow-up of the variants you generate';
                alert(value_id);
                if (value_id == 't') {
                    // update the number of variants
                    $("#clinvar_watched_title").html("Reload the page to check your ClinVar watch list");
                }
              }
              
              $("#value_to_send_" + caller).html(value_to_send);
              $("#btn_" + caller).html(label);
              //$("#contact_box").prop( "checked", false);
              if ($("#value_" + caller).attr('class') == 'w3-text-red') {
                  $("#value_" + caller).attr('class', 'w3-text-green');
              }
              else if($("#value_" + caller).attr('class') == 'w3-text-green') {
                  $("#value_" + caller).attr('class', 'w3-text-red');
              }
              $("#value_" + caller).html(txt);
              //$('#contact_box_label').html(label);
              // enable onclick
              $("span#btn_" + caller ).on("click");
              $('#btn_' +  + caller).css('cursor', 'default');
              $("html").css('cursor', 'default');
          }
          else{
              //$("#contact_box").prop( "checked", false);
              $("#error_messages").html(html_error);
              // enable onclick
              $("span#btn_" + caller ).on("click");
              $('#btn_' +  caller).css('cursor', 'default');
              $("html").css('cursor', 'default');
          }

  	});
}

function empty_variant_list(ajax_url, csrf_token) {
  // ajax to empty a user's variant favourite list
  $('html').css('cursor', 'progress');
  // send header for flask-wtf crsf security
  $.ajaxSetup({
      beforeSend: function(xhr, settings) {
          if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrf_token);
          }
      }
  });
  $.ajax({
    type: "POST",
    url: ajax_url
  })
  .done(function() {
    $('#variant_list').hide();
    $('#favourite_ul').empty();
    $('#num_favourite').text("0")
    $('#variant_list_menu').hide();
    $('#comment').text('Your list of favourites has successfully been emptied.');
    $('html').css('cursor', 'default');
    $('i.fa-star').toggleClass('fa-star fa-star-o');
    $('span[name="mark"]').attr('name', 'unmark');
  });
}

function create_unique_url(ajax_url, csrf_token) {
  // ajax to generate a unique URL coresponding to a variant list
  var reg = /^\w+$/;
  if (!reg.test($("#list_name").val())) {
    alert('Characters allowed for the list names are letters, numbers and underscores. No spaces or other characters.');
    return false;
  }
  $('html').css('cursor', 'progress');
  $('#create_unique_url').css('cursor', 'progress');
  // send header for flask-wtf crsf security
  $.ajaxSetup({
      beforeSend: function(xhr, settings) {
          if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrf_token);
          }
      }
  });
  $.ajax({
    type: "POST",
    url: ajax_url,
    data: {
      list_name: $("#list_name").val()
    }
  })
  .done(function(return_html) {
    $('#comment').html(return_html);
    $('html').css('cursor', 'default');
    $('#create_unique_url').css('cursor', 'default');
  });
}

function delete_list(ajax_url, list_name, csrf_token) {
  // ajax to delete a variant list
  $('html').css('cursor', 'progress');
  // send header for flask-wtf crsf security
  $.ajaxSetup({
      beforeSend: function(xhr, settings) {
          if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrf_token);
          }
      }
  });
  $.ajax({
    type: "GET",
    url: ajax_url,
  })
  .done(function(return_code) {
    if (return_code == 'success') {
      $('#' + list_name).hide();
    }
    else {
      $('#comment_list').html('Something went wrong with the deletion of your list. Please do not hesitate to warn us.');
    }
    $('html').css('cursor', 'default');
  });
}

function toggle_lock(ajax_url, list_name, csrf_token) {
  // ajax to delete a variant list
  $('html').css('cursor', 'progress');
  // send header for flask-wtf crsf security
  $.ajaxSetup({
      beforeSend: function(xhr, settings) {
          if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrf_token);
          }
      }
  });
  $.ajax({
    type: "GET",
    url: ajax_url,
  })
  .done(function(return_code) {
    if (return_code == 'unlocked') {
      $('#unlock_' + list_name).hide();
      $('#lock_' + list_name).show();
    }
    else if (return_code == 'locked') {
      $('#lock_' + list_name).hide();
      $('#unlock_' + list_name).show();
    }
    else{
      $('#comment_list').html('Something went wrong with the lock toggle of your list. Please do not hesitate to warn us.');
    }
    $('html').css('cursor', 'default');
  });
}
