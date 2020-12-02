function check_password_match() {
   var password = $("#password").val();
   var confirmPassword = $("#repassword").val();

   if (password != confirmPassword) {
      $("#divCheckPasswordMatch").html("<span style='color:red;'>Passwords do not match!</span>");
      $('#sub').attr('disabled', 'disabled');
   }
   else {
      $("#divCheckPasswordMatch").html("<span style='color:green;'>Passwords match.</span>");
      $('#sub').removeAttr('disabled');
   }
}

$(document).ready(function () {
   $('#sub').attr('disabled', 'disabled');
   $("#repassword").keyup(check_password_match);
});
