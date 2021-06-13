var sound_buzzer = $('#sound_buzzer')[0];
var sound_beep = $('#sound_beep')[0];
var sound_stage = $('#sound_stage')[0];

// bitmask values for 'phonetic_split_call' function
const SPLMSK_PILOT_NAME = 0x01
const SPLMSK_SPLIT_ID = 0x02
const SPLMSK_SPLIT_TIME = 0x04

/* global functions */
function supportsLocalStorage() {
	try {
		return 'localStorage' in window && window['localStorage'] !== null;
	} catch(e){
		return false;
	}
}

function median(arr){
	values = arr.concat()
	values.sort(function(a,b){
		return a-b;
	});
	if(values.length ===0) return 0;
	var half = Math.floor(values.length / 2);
	if (values.length % 2) return values[half];
	return (values[half - 1] + values[half]) / 2.0;
}

// Pad to 2 or 3 digits, default is 2
function pad(n, z=2) {
	return ('000000' + n).slice(-z);
}

function formatTimeMillis(s, timeformat='{m}:{s}.{d}') {
	s = Math.round(s);
	var ms = s % 1000;
	s = (s - ms) / 1000;
	var secs = s % 60;
	var mins = (s - secs) / 60;

	if (!formatted_time) {
		timeformat = '{m}:{s}.{d}';
	}
	var formatted_time = timeformat.replace('{d}', pad(ms, 3));
	formatted_time = formatted_time.replace('{s}', pad(secs));
	formatted_time = formatted_time.replace('{m}', mins)

	return formatted_time;
}

function colorvalToHex(color) {
	return '#' + pad(color.toString(16), 6);
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

function rgbtoHex(rgb) {
    rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
    function hex(x) {
        return ("0" + parseInt(x).toString(16)).slice(-2);
    }
    return "#" + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
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

function hexToHsl(hex) {
	var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
		r = parseInt(result[1], 16);
		g = parseInt(result[2], 16);
		b = parseInt(result[3], 16);
		r /= 255, g /= 255, b /= 255;
		var max = Math.max(r, g, b), min = Math.min(r, g, b);
		var h, s, l = (max + min) / 2;
		if(max == min){
			h = s = 0; // achromatic
		}else{
			var d = max - min;
			s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
			switch(max){
				case r: h = (g - b) / d + (g < b ? 6 : 0); break;
				case g: h = (b - r) / d + 2; break;
				case b: h = (r - g) / d + 4; break;
			}
			h /= 6;
		}
	var HSL = new Object();
	HSL['h']=h * 360;
	HSL['s']=s * 100;
	HSL['l']=l * 100;
	return HSL;
}

function LogSlider(options) {
   options = options || {};
   this.minpos = options.minpos || 0;
   this.maxpos = options.maxpos || 100;
   this.minlval = Math.log(options.minval || 1);
   this.maxlval = Math.log(options.maxval || 100000);

   this.scale = (this.maxlval - this.minlval) / (this.maxpos - this.minpos);
}
LogSlider.prototype = {
   // Calculate value from a slider position
   value: function(position) {
	  return Math.exp((position - this.minpos) * this.scale + this.minlval);
   },
   // Calculate slider position from a value
   position: function(value) {
	  return this.minpos + (Math.log(value) - this.minlval) / this.scale;
   }
};

if ( !window.performance || !window.performance.now ) {
	Date.now || ( Date.now = function () {
		return new this().getTime();
	});

	( window.performance ||
		( window.performance = {} ) ).now = function () {
			return Date.now() - offset;
		};

	var offset = ( window.performance.timing ||
		( window.performance.timing = {} ) ).navigatorStart ||
			( window.performance.timing.navigatorStart = Date.now() );
}

var keyCodeMap = {
		48:"0", 49:"1", 50:"2", 51:"3", 52:"4", 53:"5", 54:"6", 55:"7", 56:"8", 57:"9", 59:";",
		65:"a", 66:"b", 67:"c", 68:"d", 69:"e", 70:"f", 71:"g", 72:"h", 73:"i", 74:"j", 75:"k", 76:"l",
		77:"m", 78:"n", 79:"o", 80:"p", 81:"q", 82:"r", 83:"s", 84:"t", 85:"u", 86:"v", 87:"w", 88:"x", 89:"y", 90:"z",
		96:"0", 97:"1", 98:"2", 99:"3", 100:"4", 101:"5", 102:"6", 103:"7", 104:"8", 105:"9"
}

$.fn.setup_navigation = function(settings) {

	settings = jQuery.extend({
		menuHoverClass: 'show-menu',
	}, settings);

	// Add ARIA role to menubar and menu items
	$(this).attr('role', 'menubar').find('li').attr('role', 'menuitem');

	var top_level_links = $(this).find('> li > a');

	// Added by Terrill: (removed temporarily: doesn't fix the JAWS problem after all)
	// Add tabindex="0" to all top-level links
	// Without at least one of these, JAWS doesn't read widget as a menu, despite all the other ARIA
	//$(top_level_links).attr('tabindex','0');

	// Set tabIndex to -1 so that top_level_links can't receive focus until menu is open
	$(top_level_links).next('ul')
		.attr('data-test','true')
		.attr({ 'aria-hidden': 'true', 'role': 'menu' })
		.find('a')
		.attr('tabIndex',-1);

	// Adding aria-haspopup for appropriate items
	$(top_level_links).each(function(){
		if($(this).next('ul').length > 0)
			$(this).parent('li').attr('aria-haspopup', 'true');
	});

	$(top_level_links).hover(function(){
		$(this).closest('ul')
			.attr('aria-hidden', 'false')
			.find('.'+settings.menuHoverClass)
			.attr('aria-hidden', 'true')
			.removeClass(settings.menuHoverClass)
			.find('a')
			.attr('tabIndex',-1);
		$(this).next('ul')
			.attr('aria-hidden', 'false')
			.addClass(settings.menuHoverClass)
			.find('a').attr('tabIndex',0);
	});

	$(top_level_links).focus(function(){
		$(this).closest('ul')
			// Removed by Terrill
			// The following was adding aria-hidden="false" to root ul since menu is never hidden
			// and seemed to be causing flakiness in JAWS (needs more testing)
			// .attr('aria-hidden', 'false')
			.find('.'+settings.menuHoverClass)
			.attr('aria-hidden', 'true')
			.removeClass(settings.menuHoverClass)
			.find('a')
			.attr('tabIndex',-1);

	$(this).next('ul')
			.attr('aria-hidden', 'false')
			.addClass(settings.menuHoverClass)
			.find('a').attr('tabIndex',0);
	});

	// Bind arrow keys for navigation
	$(top_level_links).keydown(function(e){
		if(e.keyCode == 37) {
			e.preventDefault();
			// This is the first item
			if($(this).parent('li').prev('li').length == 0) {
				$(this).parents('ul').find('> li').last().find('a').first().focus();
			} else {
				$(this).parent('li').prev('li').find('a').first().focus();
			}
		} else if(e.keyCode == 38) {
			e.preventDefault();
			if($(this).parent('li').find('ul').length > 0) {
				$(this).parent('li').find('ul')
					.attr('aria-hidden', 'false')
					.addClass(settings.menuHoverClass)
					.find('a').attr('tabIndex',0)
					.last().focus();
			}
		} else if(e.keyCode == 39) {
			e.preventDefault();
			// This is the last item
			if($(this).parent('li').next('li').length == 0) {
				$(this).parents('ul').find('> li').first().find('a').first().focus();
			} else {
				$(this).parent('li').next('li').find('a').first().focus();
			}
		} else if(e.keyCode == 40) {
			e.preventDefault();
			if($(this).parent('li').find('ul').length > 0) {
				$(this).parent('li').find('ul')
					.attr('aria-hidden', 'false')
					.addClass(settings.menuHoverClass)
					.find('a').attr('tabIndex',0)
					.first().focus();
			}
		} else if(e.keyCode == 13 || e.keyCode == 32) {
			// If submenu is hidden, open it
			e.preventDefault();
			$(this).parent('li').find('ul[aria-hidden=true]')
					.attr('aria-hidden', 'false')
					.addClass(settings.menuHoverClass)
					.find('a').attr('tabIndex',0)
					.first().focus();
		} else if(e.keyCode == 27) {
			e.preventDefault();
			$('.'+settings.menuHoverClass)
				.attr('aria-hidden', 'true')
				.removeClass(settings.menuHoverClass)
				.find('a')
				.attr('tabIndex',-1);
		} else {
			$(this).parent('li').find('ul[aria-hidden=false] a').each(function(){
				if($(this).text().substring(0,1).toLowerCase() == keyCodeMap[e.keyCode]) {
					$(this).focus();
					return false;
				}
			});
		}
	});


	var links = $(top_level_links).parent('li').find('ul').find('a');
	$(links).keydown(function(e){
		if(e.keyCode == 38) {
			e.preventDefault();
			// This is the first item
			if($(this).parent('li').prev('li').length == 0) {
				$(this).parents('ul').parents('li').find('a').first().focus();
			} else {
				$(this).parent('li').prev('li').find('a').first().focus();
			}
		} else if(e.keyCode == 40) {
			e.preventDefault();
			if($(this).parent('li').next('li').length == 0) {
				$(this).parents('ul').parents('li').find('a').first().focus();
			} else {
				$(this).parent('li').next('li').find('a').first().focus();
			}
		} else if(e.keyCode == 27 || e.keyCode == 37) {
			e.preventDefault();
			$(this)
				.parents('ul').first()
					.prev('a').focus()
					.parents('ul').first().find('.'+settings.menuHoverClass)
					.attr('aria-hidden', 'true')
					.removeClass(settings.menuHoverClass)
					.find('a')
					.attr('tabIndex',-1);
		} else if(e.keyCode == 32) {
			e.preventDefault();
			window.location = $(this).attr('href');
		} else {
			var found = false;
			$(this).parent('li').nextAll('li').find('a').each(function(){
				if($(this).text().substring(0,1).toLowerCase() == keyCodeMap[e.keyCode]) {
					$(this).focus();
					found = true;
					return false;
				}
			});

			if(!found) {
				$(this).parent('li').prevAll('li').find('a').each(function(){
					if($(this).text().substring(0,1).toLowerCase() == keyCodeMap[e.keyCode]) {
						$(this).focus();
						return false;
					}
				});
			}
		}
	});


	// Hide menu if click or focus occurs outside of navigation
	$(this).find('a').last().keydown(function(e){
		if(e.keyCode == 9) {
			// If the user tabs out of the navigation hide all menus
			$('.'+settings.menuHoverClass)
				.attr('aria-hidden', 'true')
				.removeClass(settings.menuHoverClass)
				.find('a')
					.attr('tabIndex',-1);
		}
	});

	$(document).click(function(){ $('.'+settings.menuHoverClass).attr('aria-hidden', 'true').removeClass(settings.menuHoverClass).find('a').attr('tabIndex',-1); });

	$(this).click(function(e){
		e.stopPropagation();
	});
}


var globalAudioCtx = new (window.AudioContext || window.webkitAudioContext || window.audioContext);

var node_tone = [
	440,
	466.2,
	493.9,
	523.3,
	554.4,
	587.3,
	622.3,
	659.3
];

// context unlocking
function webAudioUnlock (context) {
	return new Promise(function (resolve, reject) {
		if (context.state === 'suspended') {
			var unlock = function() {
				context.resume().then(function() {
					$(document).off('touchstart', unlock);
					$(document).off('touchend', unlock);
					$(document).off('mouseup', unlock);

					resolve(true);
				},
				function (reason) {
					reject(reason);
				});
			};

			$(document).on('touchstart', unlock);
			$(document).on('touchend', unlock);
			$(document).on('mouseup', unlock);
		} else {
			resolve(false);
		}
	});
}

webAudioUnlock(globalAudioCtx);

// test for Firefox (has broken RamptoValue audio function)
var isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;

//Generate tone. All arguments are optional:
//duration of the tone in milliseconds. Default is 500
//frequency of the tone in hertz. default is 440
//type of tone. Possible values are sine, square, sawtooth, triangle, and custom. Default is sine.
//callback to use on end of tone
/* https://stackoverflow.com/questions/879152/how-do-i-make-javascript-beep/29641185#29641185 */
function play_beep(duration, frequency, volume, type, fadetime, callback) {
	var oscillator = globalAudioCtx.createOscillator();
	var gainNode = globalAudioCtx.createGain();

	oscillator.connect(gainNode);
	gainNode.connect(globalAudioCtx.destination);

	if (!duration)
		duration = 500;

	if (volume) {
		gainNode.gain.value = volume;
	} else {
		gainNode.gain.value = 1;
	}

	if (frequency)
		oscillator.frequency.value = frequency;
	if (type)
		oscillator.type = type;
	if (!fadetime)
		fadetime = 1;
	if (callback)
		oscillator.onended = callback;

	if(isFirefox)
		fadetime = 0;

	oscillator.start();
	setTimeout(function(fade){
		gainNode.gain.exponentialRampToValueAtTime(0.00001, globalAudioCtx.currentTime + fade);
	}, duration, fadetime);
	/*
	setTimeout(function(){
		oscillator.stop();
	}, duration + (fadetime * 1000));*/
};

function __(text) {
	// return translated string
	if (rotorhazard.language_strings[rotorhazard.interface_language]) {
		if (rotorhazard.language_strings[rotorhazard.interface_language]['values'][text]) {
			return rotorhazard.language_strings[rotorhazard.interface_language]['values'][text]
		}
	}
	return text
}

function __l(text) {
	// return translated string for local voice
	var lang = rotorhazard.voice_string_language;
	if (rotorhazard.voice_string_language == 'match-timer') {
		lang = rotorhazard.interface_language;
	}

	if (rotorhazard.language_strings[lang]) {
		if (rotorhazard.language_strings[lang]['values'][text]) {
			return rotorhazard.language_strings[lang]['values'][text]
		}
	}
	return text
}

/* Data model for nodes */
function nodeModel() {
	this.trigger_rssi = false;
	this.fObj = {
		key: '—',
		fString: 0,
		band: null,
		channel: null,
		frequency: 0
	};
	this.node_peak_rssi = false;
	this.node_nadir_rssi = false;
	this.pass_peak_rssi = false;
	this.pass_nadir_rssi = false;
	this.graphing = false;
	this.enter_at_level = false;
	this.exit_at_level = false;

	this.canvas = false;
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
	this.crossingSeries = new TimeSeries();

	this.graphPausedTime = false;
	this.graphPaused = false;
	this.pauseSeries = new TimeSeries();
}
nodeModel.prototype = {
	checkValues: function(){
		if (!this.frequency) {
			return null;
		}

		var warnings = [];

		if (this.node_nadir_rssi > 0 && this.node_nadir_rssi < this.node_peak_rssi - 20) {
			// assume node data is invalid unless nadir and peak are minimally separated
			if (this.enter_at_level > this.node_peak_rssi) {
				warnings.push(__('EnterAt is higher than NodePeak: <strong>Passes may not register</strong>. <em>Complete a lap pass before adjusting node values.</em>'));
			} else if (this.enter_at_level >= this.node_peak_rssi - 5) {
				warnings.push(__('EnterAt is very near NodePeak: <strong>Passes may not register</strong>. <em>Complete a lap pass before adjusting node values.</em>'));
			}
		}

		if (this.node_nadir_rssi > 0 && this.exit_at_level <= this.node_nadir_rssi) {
			warnings.push('ExitAt is lower than NodeNadir: <strong>Passes WILL NOT register</strong>.');
		}

		if (this.enter_at_level <= this.exit_at_level) {
			warnings.push(__('EnterAt must be greater than ExitAt: <strong>Passes WILL NOT register correctly</strong>.'));
		} else if (this.enter_at_level <= this.exit_at_level + 10) {
			warnings.push(__('EnterAt is very near ExitAt: <strong>Passes may register too frequently</strong>.'));
		}

		if (this.exit_at_level < this.pass_nadir_rssi) {
			warnings.push(__('ExitAt is lower than PassNadir: <strong>Passes may not complete</strong>.'));
		} else if (this.exit_at_level <= this.pass_nadir_rssi + 5) {
			warnings.push(__('ExitAt is very near PassNadir: <strong>Passes may not complete</strong>.'));
		}

		var output = '';
		if (warnings.length) {
			var output = $('<ul class="node-warnings">');
			for (i in warnings) {
				output.append('<li>' + warnings[i] + '</li>')
			}
		}
		return output;
	},
	setup: function(element){
		this.graph.addTimeSeries(this.series, {lineWidth:1.7,
			strokeStyle:'hsl(214, 53%, 60%)',
			fillStyle:'hsla(214, 53%, 60%, 0.4)'
		});
		this.graph.addTimeSeries(this.crossingSeries, {lineWidth:1.7,
			strokeStyle:'none',
			fillStyle:'hsla(136, 71%, 70%, 0.3)'
		});
		this.graph.streamTo(element, 200); // match delay value to heartbeat in server.py
	},
	updateThresholds: function(){
		this.graph.options.horizontalLines = [
			{color:'hsl(8.2, 86.5%, 53.7%)', lineWidth:1.7, value: this.enter_at_level}, // red
			{color:'hsl(25, 85%, 55%)', lineWidth:1.7, value: this.exit_at_level}, // orange
			// {color:'#999', lineWidth:1.7, value: this.node_peak_rssi},
			// {color:'#666', lineWidth:1.7, value: this.pass_nadir_rssi},
		];
		if (this.graphPaused) {
			this.graph.render(this.canvas, this.graphPausedTime);
		}
	}
}

/* Data model for timer */
const TONES_NONE = 0;
const TONES_ONE = 1;
const TONES_ALL = 2;
const TONES_3_2_1 = 3;

function timerModel() {
	// interval control
	this.interval = 100; // in ms
	this.min_interval = 10; // skip interval if too soon

	this.timeout = false;
	this.expected = false;
	this.next_interval = 100; // in ms

	this.callbacks = {
		'start': false,
		'stop': false,
		'step': false,
		'expire': false,
	};

	this.running = false;
	this.zero_time = null; // timestamp for timer's zero point
	this.hidden_staging = false; // display 'ready' message instead of showing time remaining
	this.staging_tones = TONES_ALL; // sound tones during staging
	this.max_delay = Infinity; // don't sound more tones than this even if staging takes longer
	this.time_s = false; // simplified relative time in seconds
	this.count_up = false; // use fixed-length timer
	this.duration = 0; // fixed-length duration, in seconds
	this.allow_expire = false; // prevent expire callbacks until timer runs 1 loop

	this.drift_history = [];
	this.drift_history_samples = 10;
	this.drift_correction = 0;

	this.warn_until = 0; // display sync warning

	var self = this;

	function step() { // timer control
		var diff = window.performance.now() - self.zero_time;
		var continue_timer = true;

		if (diff > self.interval / -2) {
			// time is positive or zero
			if (!self.count_up) {
				var new_time_s = self.duration - (Math.round(diff / 100) / 10);

				if (new_time_s != self.time_s) { // prevent double callbacks
					self.time_s = new_time_s;

					if (self.time_s <= 0) {
						continue_timer = false;
						self.running = false;
						if (self.allow_expire && self.callbacks.expire instanceof Function) {
							self.callbacks.expire(self);
						}
					} else {
						if (self.callbacks.step instanceof Function) {
							self.callbacks.step(self);
						}
					}
				}
			} else {
				var new_time_s = Math.round(diff / 100) / 10;

				if (new_time_s != self.time_s) { // prevent double callbacks
					self.time_s = new_time_s;

					if (self.callbacks.step instanceof Function) {
						self.callbacks.step(self);
					}
				}
			}
		} else {
			// negative
			var new_time_s = Math.round(diff / 100) / 10;

			if (new_time_s != self.time_s) { // prevent double callbacks
				self.time_s = new_time_s;

				if (self.callbacks.step instanceof Function) {
					self.callbacks.step(self);
				}
			}
		}

		self.allow_expire = true;

		if (continue_timer) {
			var now = window.performance.now()
			var drift = now - self.expected;
			if (drift > self.interval) {
				// self-resync if timer is interrupted (tab change, device goes to sleep, etc.)
				self.callbacks.self_resync(self);
				self.start();
			} else {
				self.get_next_step(now);
				self.timeout = setTimeout(step, Math.max(0, self.next_interval - self.drift_correction));

				self.drift_history.push(drift + self.drift_correction);
				self.drift_correction = median(self.drift_history);
				if (self.drift_history.length >= self.drift_history_samples) {
					self.drift_history.shift();
				}
			}
		}
	}

	this.get_next_step = function(now){
		// find current differential
		var diff = this.zero_time - now;

		if (diff >= 0) {
			// waiting for zero
			var to_next = diff % this.interval;
		} else {
			// timer past zero
			var to_next = this.interval + (diff % this.interval);
		}

		this.expected = now + to_next;
		this.next_interval = to_next;

		if (to_next < this.min_interval) { // skip tic if too short (prevents extra tics from delay compensation)
			this.expected += this.interval;
			this.next_interval += this.interval;
		}
	}

	this.start = function(remote_time_zero, local_remote_diiferential){
		// reset simplified time and drift history
		rotorhazard.timer.race.time_s = false;
		this.drift_history = [];
		this.drift_correction = 0;

		// get sync if needed
		if (typeof remote_time_zero !== "undefined" && typeof local_remote_diiferential !== "undefined") {
			this.sync(remote_time_zero, local_remote_diiferential);
		}

		// start timing loop
		this.continue();

		// do callback
		if (self.callbacks.start instanceof Function) {
			self.callbacks.start(this);
		}
	}

	this.continue = function(race_start_ms) {
		// begin timing loop from unknown position
		var now = window.performance.now();
		if (this.running) {
			clearTimeout(this.timeout);
		}

		this.get_next_step(now);

		this.timeout = setTimeout(step, this.next_interval);
		this.running = true;
	}

	this.sync = function(remote_time_zero, local_remote_diiferential) {
		// set local timer zero based on remote zero and calculated differential
		if (local_remote_diiferential && remote_time_zero) {
			// only valid with both components
			this.zero_time = remote_time_zero - local_remote_diiferential;
		} else {
			// otherwise don't consider valid
			this.zero_time = null;
		}
	}

	this.stop = function(){
		// stop timing
		clearTimeout(this.timeout);
		this.running = false;
		if (self.callbacks.stop instanceof Function) {
			self.callbacks.stop(this);
		}
	}

	this.renderHTML = function() {
		if (this.zero_time == null || typeof this.time_s != 'number' || !this.running) {
			return '--:--';
		}

		if (this.hidden_staging && this.time_s < 0) {
			return __l('Ready');
		}

		if (this.time_s >= 0 && !this.count_up) {
			var display_time = Math.abs(Math.ceil(this.time_s));
		} else {
			var display_time = Math.abs(Math.floor(this.time_s));
		}

		var hour = Math.floor(display_time / 3600);
		display_time = display_time - (hour * 3600);
		var minute = Math.floor(display_time / 60);
		var second = display_time % 60;

		second = (second < 10) ? '0' + second : second; // Pad zero if under 10
		minute = (minute < 10) ? '0' + minute : minute;

		if (hour) {
			return hour + ':' + minute + ':' + second;
		} else {
			return minute + ':' + second;
		}
	}
}

function parseIntOrBoolean(str) {
	if (str == 'false') {
		return 0
	}
	if (str == 'true') {
		return 1
	}
	return JSON.parse(str)
}

/* rotorhazard object for local settings/storage */
var rotorhazard = {
	raceMode: {
		0: 'Fixed time',
		1: 'No Time Limit',
	},
	startBehavior: {
		0: 'Hole Shot',
		1: 'First Lap',
		2: 'Staggered Start',
	},
	winCondition: {
		1: 'Most Laps in Fastest Time',
		5: 'Most Laps Only',
		6: 'Most Laps Only with Overtime',
		2: 'First to X Laps',
		3: 'Fastest Lap',
		4: 'Fastest 3 Consecutive Laps',
		0: 'None',
	},
	stagingTones: {
		TONES_ALL: 'Each Second',
		TONES_3_2_1: '3-2-1',
		TONES_ONE: 'One',
		TONES_NONE: 'None',
	},
	language_strings: {},
	interface_language: '',
	// text-to-speech callout options
	voice_string_language: 'match-timer', // text source language
	voice_language: '', // speech synthesis engine (browser-supplied)
	voice_volume: 1.0, // voice call volume
	voice_rate: 1.25,  // voice call speak pitch
	voice_pitch: 1.0,  // voice call speak rate
	voice_callsign: 1, // speak pilot callsigns
	voice_lap_count: 2, // speak pilot lap counts
	voice_team_lap_count: 1, // speak team lap counts
	voice_lap_time: 1, // speak lap times
	voice_race_timer: 2, // speak race timer
	voice_race_winner: 1, // speak race winner
	voice_split_timer: 0, // split timer

	tone_volume: 1.0, // race stage/start tone volume
	beep_crossing_entered: false, // beep node crossing entered
	beep_crossing_exited: false, // beep node crossing exited
	beep_manual_lap_button: false, // beep when manual lap button bit
	beep_race_leader_lap: false, // beep on lap by race leader
	beep_race_winner_declared: false, // beep on race winner declared
	beep_cluster_connect: false, // cluster timer connect / disconnect
	use_mp3_tones: false, //use mp3 tones instead of synthetic tones during Races
	beep_on_first_pass_button: false, // beep during the first pass where not voice announcment is played

	schedule_m: 0, //time in minutes for scheduled races
	schedule_s: 10, //time in minutes for scheduled races
	indicator_beep_volume: 0.5, // indicator beep volume

	//display options
	display_lap_id: false, //enables the display of the lap id
	display_time_start: false, //shows the timestamp of the lap since the race was started
	display_time_first_pass: false, //shows the timestamp of the lap since the first pass was recorded

	min_lap: 0, // minimum lap time
	admin: false, // whether to show admin options in nav
	show_messages: true, // whether to display messages
	graphing: false, // currently graphing RSSI
	primaryPilot: -1, // restrict voice calls to single pilot (default: all)
	nodes: [], // node array
	heats: {}, // heats object
	race_format: {}, // current format object

	panelstates: {}, // collapsible panel state

	// all times in ms (decimal micros if available)
	pi_time_request: false,
	pi_time_diff: false,
	race_start_pi: false,
	pi_time_diff_samples: [], // stored previously acquired offsets

	timer: {
		deferred: new timerModel(),
		race: new timerModel(),
		stopAll: function() {
			this.deferred.stop();
			this.race.stop();
		}
	},
	saveData: function() {
		if (!supportsLocalStorage()) {
			return false;
		}
		localStorage['rotorhazard.voice_string_language'] = JSON.stringify(this.voice_string_language);
		localStorage['rotorhazard.voice_language'] = JSON.stringify(this.voice_language);
		localStorage['rotorhazard.voice_volume'] = JSON.stringify(this.voice_volume);
		localStorage['rotorhazard.voice_rate'] = JSON.stringify(this.voice_rate);
		localStorage['rotorhazard.voice_pitch'] = JSON.stringify(this.voice_pitch);
		localStorage['rotorhazard.voice_callsign'] = JSON.stringify(this.voice_callsign);
		localStorage['rotorhazard.voice_lap_count'] = JSON.stringify(this.voice_lap_count);
		localStorage['rotorhazard.voice_team_lap_count'] = JSON.stringify(this.voice_team_lap_count);
		localStorage['rotorhazard.voice_lap_time'] = JSON.stringify(this.voice_lap_time);
		localStorage['rotorhazard.voice_race_timer'] = JSON.stringify(this.voice_race_timer);
		localStorage['rotorhazard.voice_race_winner'] = JSON.stringify(this.voice_race_winner);
		localStorage['rotorhazard.voice_split_timer'] = JSON.stringify(this.voice_split_timer);
		localStorage['rotorhazard.tone_volume'] = JSON.stringify(this.tone_volume);
		localStorage['rotorhazard.beep_crossing_entered'] = JSON.stringify(this.beep_crossing_entered);
		localStorage['rotorhazard.beep_crossing_exited'] = JSON.stringify(this.beep_crossing_exited);
		localStorage['rotorhazard.beep_manual_lap_button'] = JSON.stringify(this.beep_manual_lap_button);
		localStorage['rotorhazard.beep_race_leader_lap'] = JSON.stringify(this.beep_race_leader_lap);
		localStorage['rotorhazard.beep_race_winner_declared'] = JSON.stringify(this.beep_race_winner_declared);
		localStorage['rotorhazard.beep_cluster_connect'] = JSON.stringify(this.beep_cluster_connect);
		localStorage['rotorhazard.use_mp3_tones'] = JSON.stringify(this.use_mp3_tones);
		localStorage['rotorhazard.beep_on_first_pass_button'] = JSON.stringify(this.beep_on_first_pass_button);
		localStorage['rotorhazard.schedule_m'] = JSON.stringify(this.schedule_m);
		localStorage['rotorhazard.schedule_s'] = JSON.stringify(this.schedule_s);
		localStorage['rotorhazard.indicator_beep_volume'] = JSON.stringify(this.indicator_beep_volume);
		localStorage['rotorhazard.min_lap'] = JSON.stringify(this.min_lap);
		localStorage['rotorhazard.admin'] = JSON.stringify(this.admin);
		localStorage['rotorhazard.primaryPilot'] = JSON.stringify(this.primaryPilot);
		localStorage['rotorhazard.display_lap_id'] = JSON.stringify(this.display_lap_id);
		localStorage['rotorhazard.display_time_start'] = JSON.stringify(this.display_time_start);
		localStorage['rotorhazard.display_time_first_pass'] = JSON.stringify(this.display_time_first_pass);
		return true;
	},
	restoreData: function(dataType) {
		if (supportsLocalStorage()) {
			if (localStorage['rotorhazard.voice_string_language']) {
				this.voice_string_language = JSON.parse(localStorage['rotorhazard.voice_string_language']);
			}
			if (localStorage['rotorhazard.voice_language']) {
				this.voice_language = JSON.parse(localStorage['rotorhazard.voice_language']);
			}
			if (localStorage['rotorhazard.voice_volume']) {
				this.voice_volume = JSON.parse(localStorage['rotorhazard.voice_volume']);
			}
			if (localStorage['rotorhazard.voice_rate']) {
				this.voice_rate = JSON.parse(localStorage['rotorhazard.voice_rate']);
			}
			if (localStorage['rotorhazard.voice_pitch']) {
				this.voice_pitch = JSON.parse(localStorage['rotorhazard.voice_pitch']);
			}
			if (localStorage['rotorhazard.voice_callsign']) {
				this.voice_callsign = parseIntOrBoolean(localStorage['rotorhazard.voice_callsign']);
			}
			if (localStorage['rotorhazard.voice_lap_count']) {
				this.voice_lap_count = parseIntOrBoolean(localStorage['rotorhazard.voice_lap_count']);
			}
			if (localStorage['rotorhazard.voice_team_lap_count']) {
				this.voice_team_lap_count = parseIntOrBoolean(localStorage['rotorhazard.voice_team_lap_count']);
			}
			if (localStorage['rotorhazard.voice_lap_time']) {
				this.voice_lap_time = parseIntOrBoolean(localStorage['rotorhazard.voice_lap_time']);
			}
			if (localStorage['rotorhazard.voice_race_timer']) {
				this.voice_race_timer = parseIntOrBoolean(localStorage['rotorhazard.voice_race_timer']);
			}
			if (localStorage['rotorhazard.voice_race_winner']) {
				this.voice_race_winner = parseIntOrBoolean(localStorage['rotorhazard.voice_race_winner']);
			}
			if (localStorage['rotorhazard.voice_split_timer']) {
				this.voice_split_timer = JSON.parse(localStorage['rotorhazard.voice_split_timer']);
			}
			if (localStorage['rotorhazard.tone_volume']) {
				this.tone_volume = JSON.parse(localStorage['rotorhazard.tone_volume']);
			}
			if (localStorage['rotorhazard.beep_crossing_entered']) {
				this.beep_crossing_entered = JSON.parse(localStorage['rotorhazard.beep_crossing_entered']);
			}
			if (localStorage['rotorhazard.beep_crossing_exited']) {
				this.beep_crossing_exited = JSON.parse(localStorage['rotorhazard.beep_crossing_exited']);
			}
			if (localStorage['rotorhazard.beep_manual_lap_button']) {
				this.beep_manual_lap_button = JSON.parse(localStorage['rotorhazard.beep_manual_lap_button']);
			}
			if (localStorage['rotorhazard.beep_race_leader_lap']) {
				this.beep_race_leader_lap = JSON.parse(localStorage['rotorhazard.beep_race_leader_lap']);
			}
			if (localStorage['rotorhazard.beep_race_winner_declared']) {
				this.beep_race_winner_declared = JSON.parse(localStorage['rotorhazard.beep_race_winner_declared']);
			}
			if (localStorage['rotorhazard.beep_cluster_connect']) {
				this.beep_cluster_connect = JSON.parse(localStorage['rotorhazard.beep_cluster_connect']);
			}
			if (localStorage['rotorhazard.use_mp3_tones']) {
				this.use_mp3_tones = JSON.parse(localStorage['rotorhazard.use_mp3_tones']);
			}
			if (localStorage['rotorhazard.beep_on_first_pass_button']) {
				this.beep_on_first_pass_button = JSON.parse(localStorage['rotorhazard.beep_on_first_pass_button']);
			}
			if (localStorage['rotorhazard.schedule_m']) {
				this.schedule_m = JSON.parse(localStorage['rotorhazard.schedule_m']);
			}
			if (localStorage['rotorhazard.schedule_s']) {
				this.schedule_s = JSON.parse(localStorage['rotorhazard.schedule_s']);
			}
			if (localStorage['rotorhazard.indicator_beep_volume']) {
				this.indicator_beep_volume = JSON.parse(localStorage['rotorhazard.indicator_beep_volume']);
			}
			if (localStorage['rotorhazard.min_lap']) {
				this.min_lap = JSON.parse(localStorage['rotorhazard.min_lap']);
			}
			if (localStorage['rotorhazard.admin']) {
				this.admin = JSON.parse(localStorage['rotorhazard.admin']);
			}
			if (localStorage['rotorhazard.primaryPilot']) {
				this.primaryPilot = JSON.parse(localStorage['rotorhazard.primaryPilot']);
			}
			if (localStorage['rotorhazard.display_lap_id']) {
				this.display_lap_id = JSON.parse(localStorage['rotorhazard.display_lap_id']);
			}
			if (localStorage['rotorhazard.display_time_start']) {
				this.display_time_start = JSON.parse(localStorage['rotorhazard.display_time_start']);
			}
			if (localStorage['rotorhazard.display_time_first_pass']) {
				this.display_time_first_pass = JSON.parse(localStorage['rotorhazard.display_time_first_pass']);
			}
			return true;
		}
		return false;
	},
}

// deferred timer callbacks (time until race)
rotorhazard.timer.deferred.callbacks.start = function(timer){
	if (rotorhazard.timer.race.running) {  // defer timing to staging/race timers
		rotorhazard.timer.deferred.stop();
	}
}
rotorhazard.timer.deferred.callbacks.step = function(timer){
	if (rotorhazard.voice_race_timer != 0) {
		if (timer.time_s < -3600 && !(timer.time_s % -3600)) { // 2+ hour callout
			var hours = timer.time_s / -3600;
			speak('<div>' + __l('Next race begins in') + ' ' + hours + ' ' + __l('Hours') + '</div>', true);
		} else if (timer.time_s == -3600) {
			speak('<div>' + __l('Next race begins in') + ' 1 ' + __l('Hour') + '</div>', true);
		} else if (timer.time_s == -1800) {
			speak('<div>' + __l('Next race begins in') + ' 30 ' + __l('Minutes') + '</div>', true);
		} else if (timer.time_s > -60 && timer.time_s <= 300 && !(timer.time_s % 60)) { // 2–5 min callout
			var minutes = timer.time_s / -60;
			speak('<div>' + __l('Next race begins in') + ' ' + minutes + ' ' + __l('Minutes') + '</div>', true);
		} else if (timer.time_s == -60) {
			speak('<div>' + __l('Next race begins in') + ' 1 ' + __l('Minute') + '</div>', true);
		} else if (timer.time_s == -30) {
			speak('<div>' + __l('Next race begins in') + ' 30 ' + __l('Seconds') + '</div>', true);
		} else if (timer.time_s == -10) {
			speak('<div>' + __l('Next race begins in') + ' 10 ' + __l('Seconds') + '</div>', true);
		}else if (timer.time_s == -5) {
			speak('<div>' + __l('Next race begins in') + ' 5 ' + __l('Seconds') + '</div>', true);
		}
	}

	$('.time-display').html(timer.renderHTML());
}
rotorhazard.timer.deferred.callbacks.stop = function(timer){
	$('.time-display').html(timer.renderHTML());
}
rotorhazard.timer.deferred.callbacks.expire = function(timer){
	$('.time-display').html(__('Wait'));
}

// race/staging timer callbacks
rotorhazard.timer.race.callbacks.start = function(timer){
	$('.time-display').html(timer.renderHTML());
	rotorhazard.timer.deferred.stop(); // cancel lower priority timer
	if (timer.staging_tones == TONES_ONE
		&& timer.max_delay >= 1) {
		// beep on start if single staging tone
		if( rotorhazard.use_mp3_tones){
			sound_stage.play();
		}
		else {
			play_beep(100, 440, rotorhazard.tone_volume, 'triangle');
		}
	}
}

function playStageToneOnSecond(time_s){
	if (time_s * 10 % 10 == 0) {
		if( rotorhazard.use_mp3_tones){
			sound_stage.play();
		} else {
			play_beep(100, 440, rotorhazard.tone_volume, 'triangle');
		}
	}
}

rotorhazard.timer.race.callbacks.step = function(timer){
	if (timer.warn_until < window.performance.now()) {
		$('.timing-clock .warning').hide();
	}
	if (timer.time_s < 0
		&& timer.time_s >= -timer.max_delay) {
		// time before race begins (staging)
		if (timer.hidden_staging
			&& timer.staging_tones == TONES_ALL) {
			// beep every second during staging if timer is hidden
			playStageToneOnSecond(timer.time_s);
		} else if (timer.time_s == -30
			|| timer.time_s == -20
			|| timer.time_s == -10) {
			speak('<div>' + __l('Starting in') + ' ' + (-timer.time_s) + ' ' + __l('Seconds') + '</div>', true);
		} else if (timer.staging_tones == TONES_ALL
			&& timer.time_s >= -5) {
			// staging beep for last 5 seconds before start
			playStageToneOnSecond(timer.time_s);
		} else if (timer.staging_tones == TONES_3_2_1
			&& timer.time_s >= -3) {
			playStageToneOnSecond(timer.time_s);
		}
	} else if (timer.time_s == 0 ||
		(!timer.count_up && timer.time_s == timer.duration)
		) {
		// play start tone
		if( rotorhazard.use_mp3_tones){
			sound_buzzer.play();
		}
		else {
			play_beep(700, 880, rotorhazard.tone_volume, 'triangle', 0.25);
		}
	} else {
		if (!timer.count_up) {
			if (timer.time_s <= 5) { // Final seconds
				playStageToneOnSecond(timer.time_s);
			} else if (timer.time_s == 10) { // announce 10s only when counting down
				if (rotorhazard.voice_race_timer != 0)
					speak('<div>10 ' + __l('Seconds') + '</div>', true);
			}
		}

		if (rotorhazard.voice_race_timer == 1 ||
				(rotorhazard.voice_race_timer == 2 && (!timer.count_up))) {
			if (timer.time_s > 3600 && !(timer.time_s % 3600)) { // 2+ hour callout (endurance)
				var hours = timer.time_s / 3600;
				speak('<div>' + hours + ' ' + __l('Hours') + '</div>', true);
			} else if (timer.time_s == 3600) {
				speak('<div>1 ' + __l('Hour') + '</div>', true);
			} else if (timer.time_s == 1800) {
				speak('<div>30 ' + __l('Minutes') + '</div>', true);
			} else if (timer.time_s > 60 && timer.time_s <= 300 && !(timer.time_s % 60)) { // 2–5 min callout
				var minutes = timer.time_s / 60;
				speak('<div>' + minutes + ' ' + __l('Minutes') + '</div>', true);
			} else if (timer.time_s == 60) {
				speak('<div>1 ' + __l('Minute') + '</div>', true);
			} else if (timer.time_s == 30) {
				speak('<div>30 ' + __l('Seconds') + '</div>', true);
			}
		}
	}
	$('.time-display').html(timer.renderHTML());
}
rotorhazard.timer.race.callbacks.expire = function(timer){
	// play expired tone
	if( rotorhazard.use_mp3_tones){
		sound_buzzer.play();
	}
	else {
		play_beep(700, 880, rotorhazard.tone_volume, 'triangle', 0.25);
	}
	$('.time-display').html(timer.renderHTML());
}
rotorhazard.timer.race.callbacks.self_resync = function(timer){
	// display resync warning
	timer.warn_until = window.performance.now() + 3000;
	$('.timing-clock .warning').show();
}

/* global page behaviors */
var socket = false;
var standard_message_queue = [];
var interrupt_message_queue = [];

function add_to_message_queue(msg_obj, message_queue) {
	if (msg_obj.key) {
		// remove old version
		let idx = message_queue.findIndex(function(q_obj) {
			return q_obj.key === msg_obj.key;
		});
		message_queue.splice(idx, 1);
	}
	msg_obj.timestamp = new Date()
	message_queue.push(msg_obj);
}

function get_standard_message() {
	if (rotorhazard.show_messages) {
		let msgs = standard_message_queue.map(function(msg_obj) {
			return '<p>'+msg_obj.timestamp.toLocaleTimeString()+': '+msg_obj.message+'</p>'
		}).join('');
		$('#banner-msg .message').html(msgs);
		$('#banner-msg').slideDown();
	}
}

function get_interrupt_message() {
	if (rotorhazard.show_messages) {
		let msgs = interrupt_message_queue.map(function(msg_obj) {
			return '<p>'+msg_obj.timestamp.toLocaleTimeString()+': '+msg_obj.message+'</p>'
		}).join('');

		var message_el = $('<div class="priority-message-interrupt popup">');
		message_el.append('<h2>' + __('Alert') + '</h2>');
		message_el.append('<div class="popup-content">' + msgs + '</div>');

		$.magnificPopup.open({
			items: {
				src: message_el,
				type: 'inline',
			},
			callbacks: {
				afterClose: function() {
					interrupt_message_queue.length = 0;
				}
			}
		});
	}
}

function init_popup_generics() {
	$('.open-mfp-popup').magnificPopup({
		type:'inline',
		midClick: true,
	});
}

// restore local settings
if ($() && $().articulate('getVoices')[0] && $().articulate('getVoices')[0].name) {
	rotorhazard.voice_language = $().articulate('getVoices')[0].name; // set default voice
}
rotorhazard.restoreData();

if (typeof jQuery != 'undefined') {
jQuery(document).ready(function($){
	// display admin options
	if (rotorhazard.admin) {
		$('*').removeClass('admin-hide');
	}

	// populate SVG logo
	$('.rh-logo').html(svg_asset.logo);

	// header collapsing (hamburger)
	if ($('#nav-main').length) {
		$('#timer-name').after('<button class="hamburger">' + __('Menu') + '</button>');

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

		// Accessible dropdown menu
		$('#nav-main>ul').setup_navigation();

		var $menu = $('#menu'),
			$menulink = $('.menu-link'),
			$menuTrigger = $('.has-subnav > a');

		$menulink.click(function(e) {
			e.preventDefault();
			$menulink.toggleClass('active');
			$menu.toggleClass('active');
		});

		$menuTrigger.click(function(e) {
			e.preventDefault();
			var $this = $(this);
			$this.toggleClass('active').next('ul').toggleClass('active');
		});
	}

	// responsive tables
	$('table').wrap('<div class="table-wrap">');

	// Panel collapsing

	$(document).on('click', '.collapsing .panel-header', function() {
		var thisitem = $(this).parent();
		var this_id = thisitem.attr('id')
		if (thisitem.hasClass('open')) {
			thisitem.removeClass('open');
			thisitem.children('.panel-content').stop().slideUp();
			if (this_id) {
				rotorhazard.panelstates[this_id] = false;
			}
		} else {
			thisitem.addClass('open');
			thisitem.children('.panel-content').stop().slideDown();
			if (this_id) {
				rotorhazard.panelstates[this_id] = true;
			}
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
			if (panel.length && panel.children().hasClass('panel-header')) {
				panel.addClass('open').find('.panel-content').show();
				location.hash = window.location.hash;
			}
		}
	}

	$(document).on('click', 'button', function(el){
		this.blur();
	});

	// Popup generics
	init_popup_generics();

	$('.cancel').click(function() {
		$.magnificPopup.close();
	});

	// startup socket connection
	socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

	// reconnect when visibility is regained
	$(document).on('visibilitychange', function(){
		if (!document['hidden']) {
			if (!socket.connected) {
 				socket.connect();
			}
		}
	});

	// popup messaging
	socket.on('priority_message', function (msg) {
		if (msg.interrupt) {
			add_to_message_queue(msg, interrupt_message_queue);
			get_interrupt_message(interrupt_message_queue);
		} else {
			add_to_message_queue(msg, standard_message_queue);
			get_standard_message(standard_message_queue);
		}
	});

	$(document).on('click', '#banner-msg', function(el){
		$('#banner-msg').slideUp(400, function(){
			standard_message_queue.length = 0;
		});
	});

	document.onkeyup = function(e) {
		if (e.which == 27) {
			if ($('#banner-msg').is(':visible')) {
				$('#banner-msg').slideUp(400, function(){
					standard_message_queue.length = 0;
				});
			}
		}
	};

	// hard reset
	socket.on('database_restore_done', function (msg) {
		location.reload();
	});

	// load needed data from server when required
	socket.on('load_all', function (msg) {
		if (typeof(data_dependencies) != "undefined") {
			socket.emit('load_data', {'load_types': data_dependencies});
		}
	});

	// store language strings
	socket.on('all_languages', function (msg) {
		rotorhazard.language_strings = msg.languages;
	});
});
}

/* Leaderboards */
function build_leaderboard(leaderboard, display_type, meta, display_starts=false) {
	if (typeof(display_type) === 'undefined')
		display_type = 'by_race_time';
	if (typeof(meta) === 'undefined') {
		meta = new Object;
		meta.team_racing_mode = false;
		meta.start_behavior = 0;
	}

	if (meta.start_behavior == 2) {
		var total_label = __('Laps Total');
	} else {
		var total_label = __('Total');
	}

	var twrap = $('<div class="responsive-wrap">');
	var table = $('<table class="leaderboard">');
	var header = $('<thead>');
	var header_row = $('<tr>');
	header_row.append('<th class="pos"><span class="screen-reader-text">' + __('Rank') + '</span></th>');
	header_row.append('<th class="pilot">' + __('Pilot') + '</th>');
	if (meta.team_racing_mode) {
		header_row.append('<th class="team">' + __('Team') + '</th>');
	}
	if (display_starts == true) {
		header_row.append('<th class="starts">' + __('Starts') + '</th>');
	}
	if (display_type == 'by_race_time' ||
		display_type == 'heat' ||
		display_type == 'round' ||
		display_type == 'current') {
		header_row.append('<th class="laps">' + __('Laps') + '</th>');
		header_row.append('<th class="total">' + total_label + '</th>');
		header_row.append('<th class="avg">' + __('Avg.') + '</th>');
	}
	if (display_type == 'by_fastest_lap' ||
		display_type == 'heat' ||
		display_type == 'round' ||
		display_type == 'current') {
		header_row.append('<th class="fast">' + __('Fastest') + '</th>');
	}
	if (display_type == 'by_consecutives' ||
		display_type == 'heat' ||
		display_type == 'round' ||
		display_type == 'current') {
		header_row.append('<th class="consecutive">' + __('3 Consecutive') + '</th>');
	}
	header.append(header_row);
	table.append(header);

	var body = $('<tbody>');

	for (var i in leaderboard) {
		var row = $('<tr>');

		row.append('<td class="pos">'+ leaderboard[i].position +'</td>');
		row.append('<td class="pilot">'+ leaderboard[i].callsign +'</td>');
		if (meta.team_racing_mode) {
			row.append('<td class="team">'+ leaderboard[i].team_name +'</td>');
		}
		if (display_starts == true) {
			row.append('<td class="starts">'+ leaderboard[i].starts +'</td>');
		}
		if (display_type == 'by_race_time' ||
		display_type == 'heat' ||
		display_type == 'round' ||
		display_type == 'current') {
			var lap = leaderboard[i].laps;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="laps">'+ lap +'</td>');

			if (meta.start_behavior == 2) {
				var lap = leaderboard[i].total_time_laps;
			} else {
				var lap = leaderboard[i].total_time;
			}
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="total">'+ lap +'</td>');

			var lap = leaderboard[i].average_lap;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="avg">'+ lap +'</td>');
		}
		if (display_type == 'by_fastest_lap' ||
		display_type == 'heat' ||
		display_type == 'round' ||
		display_type == 'current') {
			var lap = leaderboard[i].fastest_lap;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			if (leaderboard[i].fastest_lap_source) {
				var source = leaderboard[i].fastest_lap_source;
				row.append('<td class="fast">'+ lap +'</td>');

				if (source.note) {
					var source_text = source.note
				} else {
					var source_text = __('Heat') + ' ' + source.heat;
				}
				source_text += ' / ' + __('Round') + ' ' + source.round;

				row.data('source', source_text);
				row.attr('title', source_text);
			} else {
				row.append('<td class="fast">'+ lap +'</td>');
			}

		}
		if (display_type == 'by_consecutives' ||
		display_type == 'heat' ||
		display_type == 'round' ||
		display_type == 'current') {
			var lap = leaderboard[i].consecutives;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			if (leaderboard[i].consecutives_source) {
				var source = leaderboard[i].consecutives_source;
				row.append('<td class="consecutive">'+ lap +'</td>');

				if (source.note) {
					var source_text = source.note;
				} else {
					var source_text = __('Heat') + ' ' + source.heat;
				}
				source_text += ' / ' + __('Round') + ' ' + source.round;

				row.data('source', source_text);
				row.attr('title', source_text);
			} else {
				row.append('<td class="consecutive">'+ lap +'</td>');
			}
		}

		body.append(row);
	}

	table.append(body);
	twrap.append(table);
	return twrap;
}
function build_team_leaderboard(leaderboard, display_type, meta) {
	if (typeof(display_type) === 'undefined')
		display_type = 'by_race_time';
	if (typeof(meta) === 'undefined') {
		meta = new Object;
		meta.team_racing_mode = true;
	}

	var twrap = $('<div class="responsive-wrap">');
	var table = $('<table class="leaderboard">');
	var header = $('<thead>');
	var header_row = $('<tr>');
	header_row.append('<th class="pos"><span class="screen-reader-text">' + __('Rank') + '</span></th>');
	header_row.append('<th class="team">' + __('Team') + '</th>');
	header_row.append('<th class="contribution">' + __('Contributors') + '</th>');
	if (display_type == 'by_race_time') {
		header_row.append('<th class="laps">' + __('Laps') + '</th>');
		header_row.append('<th class="total">' + __('Average Lap') + '</th>');
	}
	if (display_type == 'by_avg_fastest_lap') {
		header_row.append('<th class="fast">' + __('Average Fastest') + '</th>');
	}
	if (display_type == 'by_avg_consecutives') {
		header_row.append('<th class="consecutive">' + __('Average 3 Consecutive') + '</th>');
	}
	header.append(header_row);
	table.append(header);

	var body = $('<tbody>');

	for (var i in leaderboard) {
		var row = $('<tr>');
		row.append('<td class="pos">'+ leaderboard[i].position +'</td>');
		row.append('<td class="team">'+ leaderboard[i].name +'</td>');
		row.append('<td class="contribution">'+ leaderboard[i].contributing + '/' + leaderboard[i].members + '</td>');
		if (display_type == 'by_race_time') {
			var lap = leaderboard[i].laps;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="laps">'+ lap +'</td>');

			var lap = leaderboard[i].average_lap;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="total">'+ lap +'</td>');
		}
		if (display_type == 'by_avg_fastest_lap') {
			var lap = leaderboard[i].average_fastest_lap;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="fast">'+ lap +'</td>');
		}
		if (display_type == 'by_avg_consecutives') {
			var lap = leaderboard[i].average_consecutives;
			if (!lap || lap == '0:00.000')
				lap = '&#8212;';
			row.append('<td class="consecutive">'+ lap +'</td>');
		}

		body.append(row);
	}

	table.append(body);
	twrap.append(table);
	return twrap;
}
/* Frequency Table */
var freq = {
	frequencies: {
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
		D1: 5660,
		D2: 5695,
		D3: 5735,
		D4: 5770,
		D5: 5805,
		D6: 5880,
		D7: 5914,
		D8: 5839,
		J1: 5695,
		J2: 5770,
		J3: 5880,
		S1: 5660,
		S2: 5695,
		S3: 5735,
		S4: 5770,
		S5: 5805,
		S6: 5839,
		S7: 5878,
		S8: 5914,
	},
	getFObjbyFData: function(fData) {
		var keyNames = Object.keys(this.frequencies);

		if (fData.frequency == 0) {
			return {
				key: '—',
				fString: 0,
				band: null,
				channel: null,
				frequency: 0
			}
		}

		var fKey = "" + fData.band + fData.channel;
		if (fKey in this.frequencies) {
			if (this.frequencies[fKey] == fData.frequency) {
				return {
					key: fKey,
					fString: fKey + ':' + this.frequencies[fKey],
					band: fData.band,
					channel: fData.channel,
					frequency: fData.frequency
				}
			}
		}

		return this.findByFreq(fData.frequency)
	},
	getFObjbyKey: function(key) {
		var regex = /([A-Za-z]*)([0-9]*)/;
		var parts = key.match(regex);
		if (parts && parts.length == 3) {
			return {
				key: key,
				fString: key + ':' + this.frequencies[key],
				band: parts[1],
				channel: parts[2],
				frequency: this.frequencies[key]
			}
		}
		return false;
	},
	getFObjbyFString: function(fstring) {
		if (fstring == 0) {
			return {
				key: '—',
				fString: 0,
				band: null,
				channel: null,
				frequency: 0
			}
		}

		if (fstring == "n/a") {
			return {
				key: __("X"),
				fString: "n/a",
				band: null,
				channel: null,
				frequency: frequency
			}
		}
		var regex = /([A-Za-z]*)([0-9]*):([0-9]{4})/;
		var parts = fstring.match(regex);
		if (parts && parts.length == 4) {
			return {
				key: "" + parts[1] + parts[2],
				fString: fstring,
				band: parts[1],
				channel: parts[2],
				frequency: parts[3]
			}
		}
		return false;
	},
	getFObjbyKey: function(key) {
		var regex = /([A-Za-z]*)([0-9]*)/;
		var parts = key.match(regex);
		return {
			key: key,
			fString: key + ':' + this.frequencies[key],
			band: parts[1],
			channel: parts[2],
			frequency: this.frequencies[key]
		}
	},
	findByFreq: function(frequency) {
		if (frequency == 0) {
			return {
				key: '—',
				fString: 0,
				band: null,
				channel: null,
				frequency: 0
			}
		}
		var keyNames = Object.keys(this.frequencies);
		for (var i in keyNames) {
			if (this.frequencies[keyNames[i]] == frequency) {
				var fObj = this.getFObjbyKey(keyNames[i]);
				if (fObj) return fObj;
			}
		}
		return {
			key: __("X"),
			fString: "n/a",
			band: null,
			channel: null,
			frequency: frequency
		}
	},
	buildSelect: function() {
		var output = '<option value="0">' + __('Disabled') + '</option>';
		var keyNames = Object.keys(this.frequencies);
		for (var i in keyNames) {
			output += '<option value="' + keyNames[i] + ':' + this.frequencies[keyNames[i]] + '">' + keyNames[i] + ' ' + this.frequencies[keyNames[i]] + '</option>';
		}
		output += '<option value="n/a">' + __('N/A') + '</option>';
		return output;
	},
	/*
	updateSelects: function() {
		for (var i in rotorhazard.nodes) {
			var freqExists = $('#f_table_' + i + ' option[value=' + rotorhazard.nodes[i].frequency + ']').length;
			if (freqExists) {
				$('#f_table_' + i).val(rotorhazard.nodes[i].frequency);
			} else {
				$('#f_table_' + i).val('n/a');
			}
		}
	},
	*/
	updateBlock: function(fObj, node_idx) {
		// populate channel block
		var channelBlock = $('.channel-block[data-node="' + node_idx + '"]');
		if (fObj.frequency == 0) {
			channelBlock.children('.ch').html('—');
			channelBlock.children('.fr').html('');
		} else {
			channelBlock.children('.ch').html(fObj.key);
			channelBlock.children('.fr').html(fObj.frequency);
		}
	},
	updateBlocks: function() {
		// populate channel blocks
		for (var i in rotorhazard.nodes) {
			this.updateBlock(rotorhazard.nodes[i].fObj, i);
		}
	}
}

/* Color picker */
var color_picker_el = $('<div id="color-picker" class="popup">');
color_picker_el.append('<h2>' + __('Select Color') + '</h2>');
color_picker_el.append('<div id="color-picker-swatch">');
color_picker_el.append('<input type="range" id="color-picker-hue" min="0" max="359">');
color_picker_el.append('<input type="range" id="color-picker-sat" min="0" max="100">');
color_picker_el.append('<input type="range" id="color-picker-lum" min="25" max="100">');
color_picker_el.append('<button id="color-picker-confirm">' + __('Select') + '</button>');

function color_picker(loadColor=false, callback=false) {
	$.magnificPopup.open({
		items: {
			src: color_picker_el,
			type: 'inline',
		},
		closeOnBgClick: false,
		showCloseBtn: false,
		enableEscapeKey: true,
		callbacks: {
			open: function() {
				if (loadColor) {
					hslObj = hexToHsl(loadColor)
					$('#color-picker-hue').val(hslObj.h)
					$('#color-picker-sat').val(hslObj.s)
					$('#color-picker-lum').val(hslObj.l)
				} else {
					$('#color-picker-hue').val(212)
					$('#color-picker-sat').val(100)
					$('#color-picker-lum').val(50)
				}
				$('html').css('--color-picker-hue', $('#color-picker-hue').val());
				$('html').css('--color-picker-sat', $('#color-picker-sat').val() + '%');
				$('html').css('--color-picker-lum', $('#color-picker-lum').val() + '%');
			},
			beforeClose: function() {
				var hue = $('#color-picker-hue').val()
				var sat = $('#color-picker-sat').val()
				var lum = $('#color-picker-lum').val()
				if (typeof callback === 'function') {
					callback(hue, sat, lum);
				}
			}
		}
	});
}

$(document).on('input', '#color-picker-hue', function (event) {
	$('html').css('--color-picker-hue', $('#color-picker-hue').val());
});

$(document).on('input', '#color-picker-sat', function (event) {
	$('html').css('--color-picker-sat', $('#color-picker-sat').val() + '%');
});

$(document).on('input', '#color-picker-lum', function (event) {
	$('html').css('--color-picker-lum', $('#color-picker-lum').val() + '%');
});

$(document).on('click', '#color-picker-confirm', function(){
	$.magnificPopup.close();
})
