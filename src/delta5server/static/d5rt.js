if (typeof jQuery != 'undefined') {
jQuery(document).ready(function($){

	// full-header hamburger
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
