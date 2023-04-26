function check_password_match() {
   var password = $("#password").val();
   var confirmPassword = $("#repassword").val();

   re = /(?!^[0-9]*$)(?!^[a-z]*$)(?!^[A-Z]*$)(?!^[a-zA-Z]*$)(?!^[a-z0-9]*$)(?!^[A-Z0-9]*$)^.{8,}$/;
	if (re.test(password) === true && re.test(confirmPassword) === true) {
      if (password != confirmPassword) {
         $("#divCheckPasswordMatch").html("<span style='color:red;'>Passwords do not match!</span>");
         $("#sub").attr("disabled", "disabled");
      }
      else {
         $("#divCheckPasswordMatch").html("<span style='color:green;'>Passwords match.</span>");
         $("#sub").removeAttr("disabled");
      }
   }
   else {
      $("#divCheckPasswordMatch").html("<span style='color:red;'>Both passwords do not fill the required character mix and/or length</span>");
      $("#sub").attr("disabled", "disabled");
   }
}

$(document).ready(function () {
   $("#sub").attr("disabled", "disabled");
   $("#repassword").keyup(check_password_match);
   $("#password").keyup(check_password_match);
});