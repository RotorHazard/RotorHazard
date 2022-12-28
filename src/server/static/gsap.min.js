
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>
	<title>XFINITY</title>
	<!--CSS-->
	<link rel="stylesheet" type="text/css" media="screen" href="./cmn/css/common-min.css" />
	<!--[if IE 6]>
	<link rel="stylesheet" type="text/css" href="./cmn/css/ie6-min.css" />
	<![endif]-->
	<!--[if IE 7]>
	<link rel="stylesheet" type="text/css" href="./cmn/css/ie7-min.css" />
	<![endif]-->
	<link rel="stylesheet" type="text/css" media="print" href="./cmn/css/print.css" />
	<link rel="stylesheet" type="text/css" media="screen" href="./cmn/css/lib/jquery.radioswitch.css" />
	<link rel="stylesheet" type="text/css" media="screen" href="./cmn/css/lib/progressBar.css" />
	<!--Character Encoding-->
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <meta name="robots" content="noindex,nofollow">
	<script type="text/javascript" src="./cmn/js/lib/jquery-3.4.1.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery-migrate-1.2.1.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery.validate.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery.alerts.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery.ciscoExt.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery.highContrastDetect.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery.radioswitch.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/jquery.virtualDialog.js"></script>
	<script type="text/javascript" src="./cmn/js/utilityFunctions.js"></script>
    <script type="text/javascript" src="./cmn/js/gateway.js"></script>
	<script type="text/javascript" src="./cmn/js/lib/bootstrap.min.js"></script>
    <script type="text/javascript" src="./cmn/js/lib/bootstrap-waitingfor.js"></script>
  <script src="locale/CLDRPluralRuleParser.js"></script>
  <script src="locale/jquery.i18n.js"></script>
  <script src="locale/jquery.i18n.messagestore.js"></script>
  <script src="locale/jquery.i18n.fallbacks.js"></script>
  <script src="locale/jquery.i18n.language.js"></script>
  <script src="locale/jquery.i18n.parser.js"></script>
  <script src="locale/jquery.i18n.emitter.js"></script>
  <script src="locale/jquery.i18n.emitter.bidi.js"></script>
   <script src="locale/global.js"></script> <!-- add this -->
	<style>
		#div-skip-to {
			position:relative;
			left: 150px;
			top: -300px;
		}
		#div-skip-to a {
			position: absolute;
			top: 0;
		}
		#div-skip-to a:active, #div-skip-to a:focus {
			top: 300px;
			color: #0000FF;
			/*background-color: #b3d4fc;*/
		}
	</style>
</head>
<body>
	<!--Main Container - Centers Everything-->
	<div id="container">
		<!--Header-->
		<div id="header">
			<h2 id="logo"><img src='cmn/syndication/img/logo_xfinity.png' alt='XFINITY'  title='XFINITY' /></h2>
		</div> <!-- end #header -->
		<div id='div-skip-to' style="display: none;">
			<a id="skip-link" name="skip-link" href="#content">Skip to content</a>
		</div>
		<!--Main Content-->
		<div id="main-content">

<!-- $Id: at_a_glance.dory.jst 2943 2009-08-25 20:58:43Z slemoine $ -->
<div id="sub-header">
</div><!-- end #sub-header -->

<!--div id="nav"-->
<h1 id="index_header">Gateway > Login</h1>
<div style="float: left; margin: 0 20px 20px 0; width: 60%; height:290px;background:white;">
	<form action="check.jst" method="post" id="pageForm"  onsubmit="return f();">
	<div class="form-row">
		<p id="index_helptext">Please login to view and manage your Gateway settings.</p>
	</div>
	<div>
		<table style="background:white; text-align:center;">
			<tr>
				<td><label for="username"><b><div id="username_label">Username:</div></b></label></td>
				<td><input type="text"     id="username" name="username" style="width: 250px;" class="text" autocomplete="off" /></td>
			</tr>
			<tr>
				<td><label for="password"><b>Password:</b></label></td>
				<td><input type="password" id="password" name="password" style="width: 250px;" class="text" autocomplete="off" /></td>
			</tr>
		</table>
	</div>
	<div class="form-btn"  style="margin-top: 25px;text-align:center;">
		<input type="submit" class="btn" value="Login" />
	</div>
<input type="hidden" name="locale" id="locale" value="false">
</form>
</div>

<script type="text/javascript">
$(document).ready(function() {
	var user_type = "admin";
	gateway.page.init("Login", "nav-login");
	$("#pageForm").validate({
		errorElement : "p"
		,errorContainer : "#error-msg-box"
		,invalidHandler: function(form, validator) {
			var errors = validator.numberOfInvalids();
			if (errors) {
				var message = errors == 1 ? $.i18n("You missed 1 field. It has been highlighted") : $.i18n("You missed") + errors + $.i18n("fields. They have been highlighted");
				$("div.error").html(message);
				$("div.error").show();
			} else {
				$("div.error").hide();
			}
		}
		,rules : {
			username: {
				required: true
				,minlength: 3
			}
			,password: {
				required: true
				,minlength: 3
			}
		}
		,messages: {
			username: {
				required: $.i18n('Username cannot be blank. Please enter a valid username.')
			}
			,password: {
				required: $.i18n('Password cannot be blank. Please enter a valid password.')
				,minlength: $.i18n("Password must be at least 3 characters.")
			}
		}
	});
	$("#username").focus();
	$("#username").val("");
	$("#password").val("");
});
function f()
{
	var username;
	username = document.getElementById("username");
	username.value = (username.value.toLowerCase());
	//get the form id and submit it
	var form = document.getElementById("pageForm");
	form.submit();
	return true;
}
</script>

<!-- $Id: footer.jst 2976 2009-09-02 21:42:51Z cporto $ -->
		</div> <!-- end #main-content-->
		<!--Footer-->

		<div id="footer">
			<ul id="footer-links">
				<li class="first-child" style="width:405px;"><a href="http://www.xfinity.com" target="_blank">Xfinity.com</a></li>
			</ul>
		</div> <!-- end #footer -->
	</div> <!-- end #container -->
<script type="text/javascript">
$(document).ready(function() {
	// focus current page link, must after page.init()
	//$('#nav [href="'+location.href.replace(/^.*\//g, '')+'"]').focus();		// need a "skip nav" function
	$("#skip-link").click(function () {
        $('#content').attr('tabIndex', -1).focus();  //this is to fix skip-link doesn't work on webkit-based Chrome
    });
	// change radio-btn status and do ajax when press "enter"
	//$(".radio-btns a").keydown(function(event){
	$(".radio-btns a").keypress(function(event){
		var keycode = (event.keyCode ? event.keyCode : event.which);
		if(13 == keycode){
			if (!$(this).parent(".radio-btns").find("li").hasClass("selected")){
				return;		// do nothing if has disabled class, don't detect disabled attr for radio-btn
			}
			// console.log($(this).find(":radio").hasClass("disabled"));
			$(this).find(":radio").trigger('click');
			$(this).find(":radio").trigger('change');
			$(this).parent(".radio-btns").radioToButton();
		}
	});
	// press Esc to skip menu and goto first control of content
	// Esc:keypress:which is zero in FF, Esc:keypress is not work in Chrome
	$("#nav").keydown(function(event){
		var keycode = (event.keyCode ? event.keyCode : event.which);
		if(27 == keycode){
			$("#content textarea:eq(0)").focus();
			$("#content input:eq(0)").focus();
			$("#content a:eq(0)").focus();			// high priority element to focus			
		}
		// alert(event.keyCode+"---"+event.which+"---"+event.charCode);		
	});
	/* changes for high contrast mode */
	$.highContrastDetect({useExtraCss: true, debugInNormalMode: false});
	if ($.__isHighContrast) {
		/* change plus/minus tree indicator of nav menu */
		$("#nav a.top-level").prepend('<span class="hi_nav_top_indi">[+]</span>');
		$("#nav a.folder").prepend('<span class="hi_nav_folder_indi">[+]</span>');
		$("#nav a.top-level-active span.hi_nav_top_indi").text("[-]");
		$("#nav a.folder").click(function() {
			/* this should be called after nav state changed */
			var $link = $(this);
			if ($link.hasClass("folder-open")) {
				$link.children("span.hi_nav_folder_indi").text("[-]");
			}
			else {
				$link.children("span.hi_nav_folder_indi").text("[+]");
			}
		});
	}
	/*
	*	these 3 sections for radio-btn accessibility, as a workaround, maybe should put at the front of .ready().
	*/
	// add "role" and "title" for ARIA, attr may need to be embedded into html
	$(".radio-btns a").each(function(){
		$(this).attr("role", "radio").attr("title", $(this).closest("ul").prev().text() + $(this).find("label").text());
	});
	// monitor "aria-checked" status for JAWS, NOTE: better depends on input element
	$(".radio-btns").change(function(){
		$(this).find("a").each(function(){
			$(this).attr("aria-checked", $(this).find("input").attr("checked") ? "true" : "false");
		});
	});
	//give the initial status, do not trigger change above
	$(".radio-btns").find("a").each(function(){
		$(this).attr("aria-checked", $(this).find("input").attr("checked") ? "true" : "false");
	});

});
</script>	
</body>
</html>

