function toggle_service(pref_url, csrf_token, caller) {
    // ajax to modify prefs for email contacts
    $('html').css('cursor', 'progress');
    // send header for flask-wtf crsf security
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
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
              var label = 'Disable it';
              var value_to_send = 'f';
              if (value_id == 'f') {
                  txt = 'disabled';
                  label = 'Enable it';
                  value_to_send = 't';
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
              $("html").css('cursor', 'default');
          }
          else{
              //$("#contact_box").prop( "checked", false);
              $("#error_messages").html(html_error);
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
    $("#variant_list").hide();
    $("#num_favourite").text("0")
    $("#variant_list_menu").hide();
    $("#comment").text("Your list of favourites has successfully been emptied.");
    $('html').css('cursor', 'default');
  });
}

function create_unique_url(ajax_url, csrf_token) {
  // ajax to generate a unique URL coresponding to a variant list
  var reg = /^\w+$/;
  if (!reg.test($("#list_name").val())) {
    alert("Characters allowed for the list names are letters, numbers and underscores. No spaces or other characters.");
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
    $("#comment").html(return_html);
    $('html').css('cursor', 'default');
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
      $("#" + list_name).hide();
    }
    else {
      $("#comment_list").html('Something went wrong with teh deletion of your list. Please do not hesitate to advise us.');
    }
    $('html').css('cursor', 'default');
  });
}
