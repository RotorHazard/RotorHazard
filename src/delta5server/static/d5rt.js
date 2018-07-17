/* global functions */
function supportsLocalStorage() {
	try {
		return 'localStorage' in window && window['localStorage'] !== null;
	} catch(e){
		return false;
	}
}

/* d5rt object for local settings/storage */
var d5rt = {
	language: '',
	admin: false,
	primaryPilot: -1,

	saveData: function() {
		if (!supportsLocalStorage()) {
			return false;
		}
		localStorage['d5rt.language'] = JSON.stringify(this.language);
		localStorage['d5rt.admin'] = JSON.stringify(this.admin);
		localStorage['d5rt.primaryPilot'] = JSON.stringify(this.primaryPilot);
		return true;
	},
	restoreData: function(dataType) {
		if (supportsLocalStorage()) {
			if (localStorage['d5rt.language']) {
				this.language = JSON.parse(localStorage['d5rt.language']);
			}
			if (localStorage['d5rt.admin']) {
				this.admin = JSON.parse(localStorage['d5rt.admin']);
			}
			if (localStorage['d5rt.primaryPilot']) {
				this.primaryPilot = JSON.parse(localStorage['d5rt.primaryPilot']);
			}
			return true;
		}
		return false;
	},
}

/* global page behaviors */

if (typeof jQuery != 'undefined') {
jQuery(document).ready(function($){
	// restore local settings
	d5rt.language = $().articulate('getVoices')[0].name; // set default voice
	d5rt.restoreData();

	if (d5rt.admin) {
		$('nav li').removeClass('admin-hide');
	}

	// header collapsing (hamburger)
	$('#logo').after('<button class="hamburger">Menu</button>');

	$('.hamburger').on('click', function(event) {
		if ($('body').hasClass('nav-over')) {
			$('#header-extras').css('display', '');
			$('#nav-main').css('display', '');
			$('body').removeClass('nav-over');
		} else {
			$('#header-extras').show();
			$('#nav-main').show();
			$('body').addClass('nav-over');
		}
	});

	$('.hamburger').on('mouseenter', function(event){
		$('#header-extras').show();
		$('#nav-main').show();
		setTimeout(function(){
			$('body').addClass('nav-over');
		}, 1);
	});

	$('body>header').on('mouseleave', function(event){
		$('#header-extras').css('display', '');
		$('#nav-main').css('display', '');
		$('body').removeClass('nav-over');
	});

	$(document).on('click', function(event) {
		if (!$(event.target).closest('body>header').length) {
			$('#header-extras').css('display', '');
			$('#nav-main').css('display', '');
			$('body').removeClass('nav-over');
		}
	});


	// responsive tables
	$('table').wrap('<div class="table-wrap">');

});
}
