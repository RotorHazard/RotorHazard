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

function contrastColor(hexcolor) {
	hex = hexcolor.replace(/[^0-9A-F]/gi, '');
	var bigint = parseInt(hex, 16);
	var r = (bigint >> 16) & 255;
	var g = (bigint >> 8) & 255;
	var b = bigint & 255;

	var brightness = ((r * 299) + (g * 587) + (b * 114)) / 255000;

	// values range from 0 to 1
	// anything greater than 0.5 should be bright enough for dark text
	if (brightness >= 0.5) {
		return "#000000"
	} else {
		return "#ffffff"
	}
}

function hslToHex(h, s, l) {
	h = parseInt(h.replace(/[^0-9\.]/gi, '')) / 360;
	s = parseInt(s.replace(/[^0-9\.]/gi, '')) / 100;
	l = parseInt(l.replace(/[^0-9\.]/gi, '')) / 100;

	let r, g, b;
	if (s === 0) {
		r = g = b = l; // achromatic
	} else {
		const hue2rgb = (p, q, t) => {
			if (t < 0) t += 1;
			if (t > 1) t -= 1;
			if (t < 1 / 6) return p + (q - p) * 6 * t;
			if (t < 1 / 2) return q;
			if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
			return p;
		};
		const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
		const p = 2 * l - q;
		r = hue2rgb(p, q, h + 1 / 3);
		g = hue2rgb(p, q, h);
		b = hue2rgb(p, q, h - 1 / 3);
	}
	const toHex = x => {
		const hex = Math.round(x * 255).toString(16);
		return hex.length === 1 ? '0' + hex : hex;
	};
	return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/* d5rt object for local settings/storage */
var d5rt = {
	language: '', // local language for voice callout
	voice_volume: 1.0, // voice call volume
	voice_callsign: true, // speak pilot callsigns
	voice_lap_count: true, // speak lap counts
	voice_lap_time: true, // speak lap times
	voice_race_timer: true, // speak race timer
	tone_volume: 1.0, // race stage/start tone volume
	admin: false, // whether to show admin options in nav
	graphing: false,
	primaryPilot: -1, // restrict voice calls to single pilot (default: all)
	nodes: [], // node array
	collecting: false,
	collection_amount: 25, // number of rssi data points to capture

	saveData: function() {
		if (!supportsLocalStorage()) {
			return false;
		}
		localStorage['d5rt.language'] = JSON.stringify(this.language);
		localStorage['d5rt.voice_volume'] = JSON.stringify(this.voice_volume);
		localStorage['d5rt.voice_callsign'] = JSON.stringify(this.voice_callsign);
		localStorage['d5rt.voice_lap_count'] = JSON.stringify(this.voice_lap_count);
		localStorage['d5rt.voice_lap_time'] = JSON.stringify(this.voice_lap_time);
		localStorage['d5rt.voice_race_timer'] = JSON.stringify(this.voice_race_timer);
		localStorage['d5rt.tone_volume'] = JSON.stringify(this.tone_volume);
		localStorage['d5rt.admin'] = JSON.stringify(this.admin);
		localStorage['d5rt.primaryPilot'] = JSON.stringify(this.primaryPilot);
		return true;
	},
	restoreData: function(dataType) {
		if (supportsLocalStorage()) {
			if (localStorage['d5rt.language']) {
				this.language = JSON.parse(localStorage['d5rt.language']);
			}
			if (localStorage['d5rt.voice_volume']) {
				this.voice_volume = JSON.parse(localStorage['d5rt.voice_volume']);
			}
			if (localStorage['d5rt.voice_callsign']) {
				this.voice_callsign = JSON.parse(localStorage['d5rt.voice_callsign']);
			}
			if (localStorage['d5rt.voice_lap_count']) {
				this.voice_lap_count = JSON.parse(localStorage['d5rt.voice_lap_count']);
			}
			if (localStorage['d5rt.voice_lap_time']) {
				this.voice_lap_time = JSON.parse(localStorage['d5rt.voice_lap_time']);
			}
			if (localStorage['d5rt.voice_race_timer']) {
				this.voice_race_timer = JSON.parse(localStorage['d5rt.voice_race_timer']);
			}
			if (localStorage['d5rt.tone_volume']) {
				this.tone_volume = JSON.parse(localStorage['d5rt.tone_volume']);
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
	this.node_peak_rssi = false;
	this.pass_nadir_rssi = false;
	this.graphing = false;
	this.enter_at_level = false;
	this.exit_at_level = false;
	this.corrections = {
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
		maxValue: 1,
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
		this.graph.options.horizontalLines = [
			{color:'hsl(25, 85%, 55%)', lineWidth:1.7, value: this.enter_at_level},
			{color:'hsl(8.2, 86.5%, 53.7%)', lineWidth:1.7, value: this.node_peak_rssi},
			{color:'#999', lineWidth:1.7, value: this.exit_at_level},
			{color:'#666', lineWidth:1.7, value: this.pass_nadir_rssi},
		];
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
	$(document).on('click', '.panel-header', function() {
		var thisitem = $(this).parent();
		if (thisitem.hasClass('open')) {
			thisitem.removeClass('open');
			thisitem.children('.panel-content').slideUp();
		} else {
			thisitem.addClass('open');
			thisitem.children('.panel-content').slideDown();
		}
	});

	if ($('.collapsing').length) {
		$('.collapsing').each(function(){
			var el = $(this)
			$(el).addClass('active');

			el.find('.panel-content').hide();
			el.find('.panel-header>*').wrapInner('<button class="no-style">');
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

/* Leaderboards */
function build_leaderboard(leaderboard, display_type) {
	if (typeof(display_type) === 'undefined')
		display_type = 'current';

	var table = $('<table class="leaderboard">');
	var header = $('<thead>');
	var header_row = $('<tr>');
	header_row.append('<th class="pos">Pos.</th>');
	header_row.append('<th class="pilot">Pilot</th>');
	if (leaderboard.team_racing_mode) {
		header_row.append('<th class="team">Team</th>');
	}
	header_row.append('<th class="laps">Laps</th>');
	if (display_type == 'current') {
		header_row.append('<th class="last">Last Lap</th>');
		header_row.append('<th class="behind">Behind</th>');
	}
	header_row.append('<th class="avg">Average</th>');
	header_row.append('<th class="fast">Fastest</th>');
	header_row.append('<th class="total">Total</th>');

	header.append(header_row);
	table.append(header);

	var body = $('<tbody>');

	for (var i in leaderboard.data) {
		var row = $('<tr>');

		row.append('<td class="pos">'+ leaderboard.data[i].position +'</td>');
		row.append('<td class="pilot">'+ leaderboard.data[i].callsign +'</td>');
		if (leaderboard.data.team_racing_mode) {
			row.append('<td class="team">'+ leaderboard.data[i].team_name +'</td>');
		}
		row.append('<td class="laps">'+ leaderboard.data[i].laps +'</td>');
		if (display_type == 'current') {
			row.append('<td class="last">'+ leaderboard.data[i].last_lap +'</td>');
			row.append('<td class="behind">'+ leaderboard.data[i].behind +'</td>');
		}
		row.append('<td class="avg">'+ leaderboard.data[i].average_lap +'</td>');
		row.append('<td class="fast">'+ leaderboard.data[i].fastest_lap +'</td>');
		row.append('<td class="total">'+ leaderboard.data[i].total_time +'</td>');

		body.append(row);
	}

	table.append(body);
	return table;
}

function build_event_leaderboard(leaderboard, display_type) {
	if (typeof(display_type) === 'undefined')
		display_type = 'by_race_time';

	var table = $('<table class="leaderboard event-leaderboard">');
	var header = $('<thead>');
	var header_row = $('<tr>');
	header_row.append('<th class="pos">Pos.</th>');
	header_row.append('<th class="pilot">Pilot</th>');
	if (leaderboard.team_racing_mode) {
		header_row.append('<th class="team">Team</th>');
	}
	if (display_type == 'by_race_time') {
		header_row.append('<th class="laps">Laps</th>');
		header_row.append('<th class="total">Total</th>');
		header_row.append('<th class="avg">Average</th>');
	}
	if (display_type == 'by_fastest_lap') {
		header_row.append('<th class="fast">Fastest</th>');
	}
	header.append(header_row);
	table.append(header);

	var body = $('<tbody>');

	for (var i in leaderboard[display_type]) {
		var row = $('<tr>');

		row.append('<td class="pos">'+ leaderboard[display_type][i].position +'</td>');
		row.append('<td class="pilot">'+ leaderboard[display_type][i].callsign +'</td>');
		if (leaderboard.team_racing_mode) {
			row.append('<td class="team">'+ leaderboard[display_type][i].team_name +'</td>');
		}
		if (display_type == 'by_race_time') {
			row.append('<td class="laps">'+ leaderboard[display_type][i].laps +'</td>');
			row.append('<td class="total">'+ leaderboard[display_type][i].total_time +'</td>');
			row.append('<td class="avg">'+ leaderboard[display_type][i].average_lap +'</td>');
		}
		if (display_type == 'by_fastest_lap') {
			row.append('<td class="fast">'+ leaderboard[display_type][i].fastest_lap +'</td>');
		}

		body.append(row);
	}

	table.append(body);
	return table;
}
/* Frequency Table */
var freq = {
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
		U9: 5985,
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
	},
	updateSelects: function() {
		for (var i in d5rt.nodes) {
			var freqExists = $('#f_table_' + i + ' option[value=' + d5rt.nodes[i].frequency + ']').length;
			if (freqExists) {
				$('#f_table_' + i).val(d5rt.nodes[i].frequency);
			} else {
				$('#f_table_' + i).val('n/a');
			}
		}
	},
	updateBlocks: function() {
		// populate channel blocks
		for (var i in d5rt.nodes) {
			var channelBlock = $('.channel-block[data-node="' + i + '"]');
			channelBlock.children('.ch').html(this.findByFreq(d5rt.nodes[i].frequency));
			if (d5rt.nodes[i].frequency == 0) {
				channelBlock.children('.fr').html('');
			} else {
				channelBlock.children('.fr').html(d5rt.nodes[i].frequency);
			}
		}
	}
}

