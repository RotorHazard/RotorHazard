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

/* d5rt object for local settings/storage */
var d5rt = {
	language: '', // local language for voice callout
	admin: false, // whether to show admin options in nav
	primaryPilot: -1, // restrict voice calls to single pilot (default: all)
	nodes: [], // node array for rssi graphing
	collecting: false,
	collection_amount: 25, // number of rssi data points to capture
	rssiMax: 100,

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
	this.peak_rssi = false;
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
				maxValue: 150,
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

});
}
