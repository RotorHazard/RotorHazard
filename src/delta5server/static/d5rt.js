/* global functions */
function supportsLocalStorage() {
	try {
		return 'localStorage' in window && window['localStorage'] !== null;
	} catch(e){
		return false;
	}
}

function median(values){
	values.sort(function(a,b){
		return a-b;
	});
	if(values.length ===0) return 0;
	var half = Math.floor(values.length / 2);
	if (values.length % 2) return values[half];
	return (values[half - 1] + values[half]) / 2.0;
}

function convertColor(color) {
	if(color.substring(0,1) == '#') {
		color = color.substring(1);
	}
	var rgbColor = {};
	rgbColor.r = parseInt(color.substring(0,2),16);
	rgbColor.g = parseInt(color.substring(2,4),16);
	rgbColor.b = parseInt(color.substring(4),16);
	return rgbColor;
}

/* d5rt object for local settings/storage */
var d5rt = {
	language: '', // local language for voice callout
	admin: false, // whether to show admin options in nav
	primaryPilot: -1, // restrict voice calls to single pilot (default: all)
	nodes: [], // node array for rssi graphing
	collecting: false,
	collection_amount: 25, // number of rssi data points to capture

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

/* Data model for nodes */
function nodeModel() {
	this.trigger_rssi = false;
	this.frequency = 0;
	this.peak_rssi = false;
	this.graphing = false;
	this.calibration_threshold = false;
	this.trigger_threshold = false;
	this.offset = 0;
	this.corrections = {
		noise: {
			rawData: [],
			min: false,
			median: false,
			max: false
		},
		floor: {
			rawData: [],
			min: false,
			median: false,
			max: false
		},
		nearest: {
			rawData: [],
			min: false,
			median: false,
			max: false
		},
		gate: {
			rawData: [],
			min: false,
			median: false,
			max: false
		},

		median_separation: false,
		suggestedScale: 1,

		calOffset: {
			min: 0,
			best: 0,
			max: Infinity
		},
		calThrs: {
			min: 0,
			best: 0,
			max: Infinity
		},
		trigThrs: {
			min: 0,
			best: 0,
			max: Infinity
		}
	};

	this.graph = new SmoothieChart({
				responsive: true,
				millisPerPixel:50,
				grid:{
					strokeStyle:'rgba(255,255,255,0.25)',
					sharpLines:true,
					verticalSections:0,
					borderVisible:false
				},
				labels:{
					precision:0
				},
				maxValue: 0,
				minValue: 0,
			});
	this.series = new TimeSeries();
}
nodeModel.prototype = {
	setup: function(element){
		this.graph.addTimeSeries(this.series, {lineWidth:1.7,
			strokeStyle:'hsl(214, 53%, 60%)',
			fillStyle:'hsla(214, 53%, 60%, 0.4)'
		});
		this.graph.streamTo(element, 250); // match delay value to heartbeat in server.py
	},
	updateThresholds: function(){
		if (this.trigger_threshold) {
			this.graph.options.horizontalLines = [
				{color:'hsl(25, 85%, 55%)', lineWidth:1.7, value: this.trigger_rssi},
				{color:'hsl(8.2, 86.5%, 53.7%)', lineWidth:1.7, value: this.peak_rssi},
				{color:'#999', lineWidth:1.7, value: this.trigger_threshold},
				{color:'#666', lineWidth:1.7, value: this.calibration_threshold},
			];
		} else if (this.trigger_rssi) {
			this.graph.options.horizontalLines = [
				{color:'hsl(25, 85%, 55%)', lineWidth:1.7, value: this.trigger_rssi},
				{color:'hsl(8.2, 86.5%, 53.7%)', lineWidth:1.7, value: this.peak_rssi},
			];
		}
	},
	calcStats: function(dataType, selfIndex) {
		dataSet = this.corrections[dataType];
		dataSet.max = Math.max(...dataSet.rawData);
		dataSet.min = Math.min(...dataSet.rawData);
		dataSet.median = median(dataSet.rawData);
		// dataSet.range = dataSet.max - dataSet.min;

		$('#max_' + dataType + '_' + selfIndex).html(dataSet.max);
		$('#median_' + dataType + '_' + selfIndex).html(dataSet.median);
		$('#min_' + dataType + '_' + selfIndex).html(dataSet.min);
	}
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

	// Panel collapsing
	if ($('.collapsing').length) {
		$('.collapsing').each(function(){
			var el = $(this)
			$(el).addClass('active');

			el.find('.panel-content').hide();
			el.find('.panel-header>*').wrapInner('<button class="no-style">');
			el.find('.panel-header').click(function(){
				var thisitem = $(this).parent();
				if (thisitem.hasClass('open')) {
					thisitem.removeClass('open');
					thisitem.find('.panel-content').slideUp();
				} else {
					thisitem.addClass('open');
					thisitem.find('.panel-content').slideDown();
				}
			});
		});

		if(window.location.hash) {
			var panel = $(window.location.hash);
			if (panel.length() && panel.children().hasClass('panel-header')) {
				panel.addClass('open').find('.panel-content').show();
				location.hash = window.location.hash;
			}
		}
	}
});
}

/* Frequency Table */

var freqTable = {
	frequencies: {
		'—': 0,
		R1: 5658,
		R2: 5695,
		R3: 5732,
		R4: 5769,
		R5: 5806,
		R6: 5843,
		R7: 5880,
		R8: 5917,
		F1: 5740,
		F2: 5760,
		F3: 5780,
		F4: 5800,
		F5: 5820,
		F6: 5840,
		F7: 5860,
		F8: 5880,
		E1: 5705,
		E2: 5685,
		E3: 5665,
		E4: 5645,
		E5: 5885,
		E6: 5905,
		E7: 5925,
		E8: 5945,
		B1: 5733,
		B2: 5752,
		B3: 5771,
		B4: 5790,
		B5: 5809,
		B6: 5828,
		B7: 5847,
		B8: 5866,
		A1: 5865,
		A2: 5845,
		A3: 5825,
		A4: 5805,
		A5: 5785,
		A6: 5765,
		A7: 5745,
		A8: 5725,
		L1: 5362,
		L2: 5399,
		L3: 5436,
		L4: 5473,
		L5: 5510,
		L6: 5547,
		L7: 5584,
		L8: 5621,
		U0: 5300,
		U1: 5325,
		U2: 5348,
		U3: 5366,
		U4: 5384,
		U5: 5402,
		U6: 5420,
		U7: 5438,
		U8: 5456,
		'N/A': 'n/a'
	},
	findByFreq: function(frequency) {
		var keyNames = Object.keys(this.frequencies);
		for (var i in keyNames) {
			if (this.frequencies[keyNames[i]] == frequency) {
				return keyNames[i];
			}
		}
		return false;
	},
	buildSelect: function() {
		var output = '';
		var keyNames = Object.keys(this.frequencies);
		for (var i in keyNames) {
			if (this.frequencies[keyNames[i]] == 0) {
				output += '<option value="0">Disabled</option>';
			} else if (this.frequencies[keyNames[i]] == 'n/a') {
				output += '<option value="n/a">N/A</option>';
			} else {
				output += '<option value="' + this.frequencies[keyNames[i]] + '">' + keyNames[i] + ' ' + this.frequencies[keyNames[i]] + '</option>';
			}
		}
		return output;
	}
}

