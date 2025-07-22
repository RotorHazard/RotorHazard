/* Marshaling functions */

class RHMarshal {
	self = false;
	socket = false;

	elements = {
		graph_canvas_id: false,
		graph_canvas: false,
	}

	time_format = null;

	callbacks = {
		calcLaps: false,
		calibration: false,
		clearMarkedLap: false,
		displayLaps: false,
		graphInteractCancel: false,
		graphInteractTap: false,
		recalcRace: false,
	}

	race = {
		history_times: null,
		history_values: null,
		laps: null,
		enter_at: null,
		exit_at: null,
		start_time: null,
		end_time: null,
	}

	// Internal
	graph = false;
	graph_series = {
		rssi: false,
		lap_marker: false,
		deleted_lap: false,
		selection: false,
	}
	race_loaded = false;

	// interactions
	interact = {
		canDrag: false,
		isDragging: false,
		startingEnter: false,
		startingExit: false,
		startingX: false,
		startingY: false,
		adjustEnter: true,
		isTouchEvent: false,
	}

	constructor(options) {
		self = this;
		self.socket = options.socket;
		self.elements.graph_canvas_id = options.elements.graph_canvas_id;
		self.time_format = options.time_format;
		self.callbacks.calcLaps = options.callbacks.calcLaps;
		self.callbacks.calibration = options.callbacks.calibration;
		self.callbacks.clearMarkedLap = options.callbacks.clearMarkedLap;
		self.callbacks.displayLaps = options.callbacks.displayLaps;
		self.callbacks.graphInteractCancel = options.callbacks.graphInteractCancel;
		self.callbacks.graphInteractTap = options.callbacks.graphInteractTap;
		self.callbacks.recalcRace = options.callbacks.recalcRace;

		if (document.readyState !== 'loading') {
			self.atDOMReady();
		} else {
			document.addEventListener('DOMContentLoaded', self.atDOMReady);
		}
	}

	atDOMReady() {
		self.elements.graph_canvas = document.getElementById(self.elements.graph_canvas_id)
		self.graphSetup();

		//mouse/touch check
		$(document).on('mouseup', function(){
			if (!self.isTouchEvent) {
				self.canDrag = false;
				self.isDragging = false;
			}
			self.isTouchEvent = false;
		});

		// mouse handlers
		$(self.elements.graph_canvas).on('mousedown', self.graphInteractMouseDown);
		$(self.elements.graph_canvas).on('mousemove', self.graphInteractMouseMove);
		$(self.elements.graph_canvas).on('mouseup', self.graphInteractMouseUp);
		$(self.elements.graph_canvas).on('mouseout', self.graphInteractMouseOut);

		// touch handlers
		$(self.elements.graph_canvas).on('touchstart', self.graphInteractTouchStart);
		$(self.elements.graph_canvas).on('touchmove', self.graphInteractTouchMove);
		$(self.elements.graph_canvas).on('touchend', self.graphInteractTouchEnd);
		$(self.elements.graph_canvas).on('touchCancel', self.graphInteractTouchCancel);

		// graph resize catch
		var resizeTimer;
		$(window).on('resize', function(){
			if (self.race_loaded) {
				clearTimeout(resizeTimer);
				resizeTimer = setTimeout(function() {
					self.renderGraph();
				}, 250);
			}
		});
	}

	graphSetup() {
		self.context = self.elements.graph_canvas.getContext('2d');
		self.graph = new SmoothieChart({
			interpolation: 'step',
			responsive: true,
			grid:{
				strokeStyle:'rgba(255,255,255,0.1)',
				millisPerLine:30, // Smoothie thinks the timestamps are in seconds
				sharpLines:true,
				verticalSections:0,
				borderVisible:false
			},
			labels:{
				precision: 0
			},
			scaleSmoothing: 1
		});
		self.graph_series.rssi = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.rssi, {
			lineWidth: 1.7,
			strokeStyle:'hsl(214, 53%, 60%)',
			fillStyle:'hsla(214, 53%, 60%, 0.4)'
		});
		self.graph_series.lap_marker = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.lap_marker, {
			lineWidth: 1.7,
			strokeStyle:'none',
			fillStyle:'hsla(136, 71%, 70%, 0.3)'
		});
		self.graph_series.deleted_lap = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.deleted_lap, {
			lineWidth: 1.7,
			strokeStyle:'none',
			fillStyle:'hsla(8.2, 86.5%, 53.7%, 0.2)'
		});
		self.graph_series.selection = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.selection, {
			lineWidth: 1.7,
			strokeStyle:'hsl(70, 60%, 60%)',
			lineWidth: 3
		});
		self.graph_series.race_end = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.race_end, {
			strokeStyle:'none',
			fillStyle:'hsla(0, 0%, 100%, 0.15)'
		});

		self.graph.streamTo(self.elements.graph_canvas, 1);
		self.graph.stop();
	}

	setRaceData(args) {
		self.race.calc_result = {};
		// fill current data with race meta
		self.race.round_id = args.round;
		self.race.heat_id = args.heat;
		self.race.race_id = args.race_id;
		self.race.class_id = args.class_id;
		self.race.format_id = args.format_id;
		self.race.start_time = args.start_time;
		self.race.start_time_formatted = args.start_time_formatted;
	}

	setPilotData(args) {
		self.race.pilotrace_index = args.pilot;
		self.race.history_times = args.history_times;
		self.race.history_values = args.history_values;
		self.race.laps = args.laps;
		self.race.enter_at = args.enter_at;
		self.race.exit_at = args.exit_at;
	}

	initRace() {
		// set initial display of loaded data
		self.race_loaded = true;
		if (self.race.history_times.length) {
			self.race.end_time = self.race.history_times[self.race.history_times.length - 1];
			self.graph.options.minValue = Math.min.apply(null, self.race.history_values) - 2;
			self.graph.options.maxValue = Math.max.apply(null, self.race.history_values) + 2;
		} else {
			self.race.end_time = self.race.start_time + 1
			self.graph.options.minValue = self.race.exit_at;
			self.graph.options.maxValue = self.race.enter_at;
		}

		self.race.history_duration = self.race.end_time - self.race.start_time;

		if (self.race.format_id > 0) {
			self.race.race_format = rotorhazard.event.race_formats.find(obj => {return obj.id == self.race.format_id});
		} else {
			self.race.race_format = {
				unlimited_time: false,
				race_time_sec: null
			};
		}

		// prepare graph
		self.graph_series.rssi.data = [];
		for (var idx in self.race.history_times) {
			var value = self.race.history_times[idx];
			if (value == lastValue) {
				self.graph_series.rssi.append((self.race.history_times[idx] - self.race.start_time) + 0.001, self.race.history_values[idx]);
			} else {
				self.graph_series.rssi.append((self.race.history_times[idx] - self.race.start_time), self.race.history_values[idx]);
			}
			var lastValue = value;
		}

		// display race end
		self.graph_series.race_end.clear();
		self.graph_series.race_end.data = [];
		if (self.race.race_format.race_time_sec) {
			// convert lap time to history time
			var finish_time = self.race.race_format.race_time_sec;
			// highlight the lap
			self.graph_series.race_end.append(0, self.graph.options.minValue - 10);
			self.graph_series.race_end.append(finish_time - .001, self.graph.options.minValue - 10);
			self.graph_series.race_end.append(finish_time, self.graph.options.maxValue + 10);
			self.graph_series.race_end.append(self.race.history_duration + .001, self.graph.options.maxValue + 10);
		}

		// Lap marker series lines drawn below the bottom of the graph
		self.clearCrossings();
		self.clearMarkedLap();
		self.renderGraph();

		// populate laps
		self.displayLaps(self.race.laps);
	}

	setEnter(rssi) {
		var chk_val = Math.min(rssi, self.graph.options.maxValue);
		chk_val = Math.max(chk_val, self.graph.options.minValue);

		if (chk_val < self.race.exit_at)  {
			chk_val = self.race.exit_at;
		}
		self.race.enter_at = chk_val;

		if (rssi < self.race.exit_at) {
			self.race.exit_at = rssi;
		}
		if (typeof self.callbacks.calibration === 'function') {
			self.callbacks.calibration({
				enter: self.race.enter_at,
				exit: self.race.exit_at,
			});
		}
		self.refreshDisplay();
	}

	setExit(rssi) {
		var chk_val = Math.min(rssi, self.graph.options.maxValue);
		chk_val = Math.max(chk_val, self.graph.options.minValue);

		if (chk_val > self.race.enter_at)  {
			chk_val = self.race.enter_at;
		}
		self.race.exit_at = chk_val;

		if (rssi > self.race.enter_at) {
			self.race.enter_at = rssi;
		}
		if (typeof self.callbacks.calibration === 'function') {
			self.callbacks.calibration({
				enter: self.race.enter_at,
				exit: self.race.exit_at,
			});
		}
		self.refreshDisplay();
	}

	refreshDisplay() {
		self.clearMarkedLap();
		self.graph_series.lap_marker.clear();
		self.graph_series.deleted_lap.clear();
		self.recalcRace();
	}

	clearCrossings() {
		self.graph_series.lap_marker.clear();
		self.graph_series.lap_marker.append(-10, self.graph.options.minValue - 10);
		self.graph_series.deleted_lap.clear();
		self.graph_series.deleted_lap.append(-10, self.graph.options.minValue - 10);
	}

	drawLap(lap, active=true) {
		if (active) {
			var series = self.graph_series.lap_marker
		} else {
			var series = self.graph_series.deleted_lap
		}

		series.append(lap.crossingStart - self.race.start_time - 0.001, self.graph.options.minValue - 10);
		series.append(lap.crossingStart - self.race.start_time, self.graph.options.maxValue + 10);
		series.append(lap.crossingEnd - self.race.start_time, self.graph.options.maxValue + 10);
		series.append(lap.crossingEnd - self.race.start_time + 0.001, self.graph.options.minValue - 10);
	}

	markLap(lap_time_stamp) {
		// convert lap time to history time
		var history_time_stamp = lap_time_stamp / 1000;
		self.graph_series.selection.clear();
		// highlight the lap
		self.graph_series.selection.append(0, self.graph.options.minValue - 10);
		self.graph_series.selection.append(history_time_stamp - .001, self.graph.options.minValue - 10);
		self.graph_series.selection.append(history_time_stamp, self.graph.options.maxValue + 10);
		self.graph_series.selection.append(history_time_stamp + .001, self.graph.options.maxValue + 10);
		self.graph_series.selection.append(history_time_stamp + .002, self.graph.options.minValue - 10);
	}

	clearMarkedLap() {
		self.graph_series.selection.clear();
		self.graph_series.selection.append(-10, self.graph.options.minValue - 10);
		if (typeof self.callbacks.clearMarkedLap === 'function') {
			self.callbacks.clearMarkedLap();
		}
	}

	renderGraph() {
		var graphWidth = self.elements.graph_canvas.offsetWidth;
		var span = self.race.history_duration / graphWidth;

		self.graph.options.millisPerPixel = span;
		self.graph.options.horizontalLines = [
			{color:'hsl(8.2, 86.5%, 53.7%)', lineWidth:1.7, value: self.race.enter_at}, // red
			{color:'hsl(25, 85%, 55%)', lineWidth:1.7, value: self.race.exit_at}, // orange
		];

		self.graph.render(self.elements.graph_canvas, self.race.history_duration);
	}

	clearGraph(){
		self.context.clearRect(0, 0, self.elements.graph_canvas.width, self.elements.graph_canvas.height);
	}

	processRXData() {
		var crossing = false;
		var crossingStart = 0;
		var crossingEnd = 0;
		var peakRssi = 0;
		var peakFirst = 0;
		var peakLast = 0;
		var laps = [];
		var startThreshLowerFlag = false;

		// set lower EnterAt/ExitAt values at race start if configured
		if (start_thresh_lower_amount > 0 && start_thresh_lower_duration > 0) {
			var diffVal = (self.race.enter_at - self.race.exit_at) * start_thresh_lower_amount / 100;
			if (diffVal > 0) {
				self.race.enter_at = self.race.enter_at - diffVal;
				self.race.exit_at = self.race.exit_at - diffVal;
				startThreshLowerFlag = true;
			}
		}

		var last_lap_time_stamp = -Infinity;
		for(var idx in self.race.history_values) {
			var rssi = self.race.history_values[idx];
			var time = self.race.history_times[idx];

			if (startThreshLowerFlag) {
				// if initial pass recorded or past duration then restore EnterAt/ExitAt values
				if (laps.length > 0 || time >= self.race.start_time + start_thresh_lower_duration + self.race.race_format.start_delay_max) {
					self.race.enter_at = self.race.enter_at;
					self.race.exit_at = self.race.exit_at;
					startThreshLowerFlag = false;
				}
			}

			if (!crossing && (rssi > self.race.enter_at)) {
				crossing = true;
				crossingStart = time;
			}

			if (rssi >= peakRssi) {
				peakLast = time;

				if (rssi > peakRssi) {
					peakFirst = time;
					peakRssi = rssi;
				}
			}

			if (crossing) {
				if (rssi < self.race.exit_at) {
					var lap_time_stamp = (((peakLast + peakFirst) / 2) - self.race.start_time) * 1000; // zero stamp within race

					if (lap_time_stamp > 0) { // reject passes before race start
						var crossingEnd = time;
						var lapdata = {
							crossingStart: crossingStart,
							crossingEnd: crossingEnd,
							lap_time_stamp: lap_time_stamp, // zero stamp within race
							source: 2, // recalc
							deleted: false
						};
						if (min_lap_behavior && lap_time_stamp < last_lap_time_stamp + min_lap) {
							lapdata.deleted = true;
						}
						laps.push(lapdata);
					}
					crossing = false;
					peakRssi = 0;
					last_lap_time_stamp = lap_time_stamp;
				}
			}
		}

		if (crossing) { // check for crossing at data end
				var lap_time_stamp = (((peakLast + peakFirst) / 2) - self.race.start_time) * 1000; // zero stamp within race

				var crossingEnd = time;
				laps.push({
					crossingStart: crossingStart,
					crossingEnd: crossingEnd,
					lap_time_stamp: lap_time_stamp, // zero stamp within race
					source: 2, // recalc
					deleted: false
				});
		}

		// auto-delete late laps
		var finished = false;
		for (var lap_i in laps) {
			var lap = laps[lap_i];
			if (finished) {
				lap.deleted = true;
			} else if (!self.race.race_format.unlimited_time && lap.lap_time_stamp > (self.race.race_format.race_time_sec * 1000)) {
				finished = true;
			}
		}
		self.race.calc_result = laps;
	}

	calcLaps() {
		self.processRXData();

		// redraw crossings
		self.clearCrossings();
		for (var lap_i in self.race.calc_result) {
			var lap = self.race.calc_result[lap_i];

			self.graph_series.lap_marker.append(lap.crossingStart - self.race.start_time - 0.001, self.graph.options.minValue - 10);
			self.graph_series.lap_marker.append(lap.crossingStart - self.race.start_time, self.graph.options.maxValue + 10);
			self.graph_series.lap_marker.append(lap.crossingEnd - self.race.start_time, self.graph.options.maxValue + 10);
			self.graph_series.lap_marker.append(lap.crossingEnd - self.race.start_time + 0.001, self.graph.options.minValue - 10);
		}

		if (typeof self.callbacks.calcLaps === 'function') {
			self.callbacks.calcLaps();
		}
	}

	recalcRace() {
		self.calcLaps();
		if (race_loaded) {
			var laps = self.race.calc_result;
			for (var lap_i in self.race.laps) {
				var lap = self.race.laps[lap_i];
				if (lap.source == 1 || lap.source == 4) { // LapSource.MANUAL = 1, LapSource.API = 4
					laps.push(lap);
				}
			}
			self.race.laps = laps;
			self.updateIncrementalLapTimes();
			self.displayLaps(laps);
			self.renderGraph();
		}
		if (typeof self.callbacks.recalcRace === 'function') {
			self.callbacks.recalcRace(race_loaded);
		}
	}

	updateIncrementalLapTimes() {
		// sorts laps table and calculates/updates "lap time" values based on lap-to-lap comparison
		self.race.laps.sort(function(a, b){
			return a.lap_time_stamp - b.lap_time_stamp
		})

		var lap_index = 0;
		for (var lap_i in self.race.laps) {
			var lap = self.race.laps[lap_i];
			if (!lap.deleted) {
				if (lap_index) {
					lap.lap_time = lap.lap_time_stamp - lastLap.lap_time_stamp;
				} else {
					lap.lap_time = lap.lap_time_stamp;
				}
				lap.lap_time_formatted = lap.lap_time / 1000; // ***
				lap_index++;
				var lastLap = lap;
			} else {
				lap.lap_time = 0;
				lap.lap_time_formatted = '-';
			}
		}
	}

	addManualLap(lap_time_s) {
		if (!self.race_loaded) {
			return false;
		}

		self.race.laps.push({
			crossingStart: 0,
			crossingEnd: 0,
			lap_time_stamp: parseInt(lap_time_s * 1000),
			source: 1,
			deleted: false
		});
		self.updateIncrementalLapTimes();
		self.clearMarkedLap();
		self.displayLaps(self.race.laps);
		self.renderGraph();
		return true;
	}

	markLapDeleted(lap_index) {
		self.race.laps[lap_index].deleted = true;
		self.clearMarkedLap();
		self.updateIncrementalLapTimes();
		self.displayLaps();
		self.renderGraph();
	}

	restoreDeletedLap(lap_index) {
		self.race.laps[lap_index].deleted = false;
		self.updateIncrementalLapTimes();
		self.displayLaps();
		self.renderGraph();
	}

	cleanDeletedLaps() {
		if (!self.race_loaded) {
			return false;
		}

		var laps = [];
		for (var lap_i in self.race.laps) {
			var lap = self.race.laps[lap_i];
			if (!lap.deleted) {
				laps.push(lap);
			}
		}
		self.race.laps = laps;

		self.clearMarkedLap();
		self.displayLaps(self.race.laps);
		self.renderGraph();
		return true;
	}

	saveLaps() {
		if (!self.race_loaded) {
			return false;
		}

		var data = {
			heat_id: self.race.heat_id,
			round_id: self.race.round_id,
			callsign: self.race.callsign,
			race_id: self.race.race_id,
			pilotrace_id: self.race.pilotrace_id,
			node: self.race.node_index,
			pilot_id: self.race.pilot_id,
			laps: self.race.laps,
			enter_at: self.race.enter_at,
			exit_at: self.race.exit_at,
		}
		self.socket.emit('resave_laps', data);

		return true;
	}

	displayLaps() {
		self.clearCrossings();
		if (typeof self.callbacks.displayLaps === 'function') {
			self.callbacks.displayLaps(self.race.laps);
		}
	}

	mapRange(val, start, end){
		return val * (end - start) / 1 + start;
	}

	handleGraphInteractionStart(evt) {
		if (evt.targetTouches) {
			var x = (evt.targetTouches[0].pageX - evt.target.offsetLeft) / evt.target.offsetWidth;
			var y = (evt.targetTouches[0].pageY - evt.target.offsetTop) / evt.target.offsetHeight;
		} else {
			var x = (evt.pageX - evt.target.offsetLeft) / evt.target.offsetWidth;
			var y = (evt.pageY - evt.target.offsetTop) / evt.target.offsetHeight;
		}

		var rssi = parseInt(self.mapRange(y, self.graph.options.maxValue, self.graph.options.minValue));

		self.interact.startingEnter = self.race.enter_at;
		self.interact.startingExit = self.race.exit_at;
		self.interact.startingX = x;
		self.interact.startingY = y;

		if (self.interact.startingEnter > self.graph.options.maxValue) {
			self.interact.adjustEnter = true;
		} else if (self.interact.startingExit < self.graph.options.minValue) {
			self.interact.adjustEnter = false;
		} else {
			var midPoint = (
				self.interact.startingEnter
			 	+ self.interact.startingExit) >> 1;
			self.interact.adjustEnter = (rssi >= midPoint);
		}
	}

	handleGraphInteractionMove(evt) {
		// user drags on graph
		if (evt.targetTouches) {
			var y = (evt.targetTouches[0].pageY - evt.target.offsetTop) / evt.target.offsetHeight;
		} else {
			var y = (evt.pageY - evt.target.offsetTop) / evt.target.offsetHeight;
		}

		if (Math.abs(y - self.interact.startingY) > 0.01 || self.interact.isDragging) { // prevent accidental drag
			self.interact.isDragging = true;

			var rssi = parseInt(self.mapRange(y, self.graph.options.maxValue, self.graph.options.minValue));

			if (self.interact.adjustEnter) {
				self.setEnter(rssi);
			} else {
				self.setExit(rssi);
			}
		}
	}

	handleGraphInteractionTap(evt) {
		// user taps but does not drag
		var time = self.mapRange(self.interact.startingX, self.race.start_time, self.race.end_time);

		if (!$.isEmptyObject(self.calc_result)) {
			// find closest start/end time to "time" point
			var delta = Infinity;
			var selectedLap = null;
			for (var i in self.calc_result) {
				var lap = self.calc_result[i];

				if (time > lap.crossingEnd) {
					selectedLap = i;
					delta = Math.abs(time - lap.crossingEnd);
				} else if (time >= lap.crossingStart
					&& time <= lap.crossingEnd) {
					selectedLap = i;
					break;
				} else {
					diff = Math.abs(time - lap.crossingStart);
					if (diff < delta) {
						selectedLap = i;
					}
					break;
				}
			}

			if (typeof self.callbacks.graphInteractTap === 'function') {
				self.callbacks.graphInteractTap({
					'lapTimeStamp': self.calc_result[selectedLap].lap_time_stamp,
				});
			}
		} else {
			self.recalcRace();
		}
	}

	handleGraphInteractionCancel() {
		if (typeof self.callbacks.graphInteractCancel === 'function') {
			self.callbacks.graphInteractCancel({
				'startingEnter': self.interact.startingEnter,
				'startingExit': self.interact.startingExit,
			});
		}
		self.race.enter_at = self.interact.startingEnter;
		self.race.exit_at = self.interact.startingExit;
		self.recalcRace();
	}

	// mouse handlers
	graphInteractMouseDown(evt) {
		if (!self.interact.isTouchEvent) {
			self.interact.canDrag = true;
			self.handleGraphInteractionStart(evt);
		}
	}

	graphInteractMouseMove(evt) {
		if (!self.interact.isTouchEvent) {
			if (self.interact.canDrag) {
				self.handleGraphInteractionMove(evt);
				self.recalcRace();
			}
		}
	}

	graphInteractMouseUp(evt){
		if (!self.interact.isTouchEvent) {
			if (self.interact.isDragging) {
				self.recalcRace();
			} else {
				self.handleGraphInteractionTap(evt);
			}
			self.interact.canDrag = false;
			self.interact.isDragging = false;
		}
		self.interact.isTouchEvent = false;
	}

	graphInteractMouseOut(evt){
		if (!self.interact.isTouchEvent) {
			if (self.interact.isDragging) {
				self.handleGraphInteractionCancel();
			}
		}
		self.interact.isTouchEvent = false;
	}

	// touch handlers
	graphInteractTouchStart(evt) {
		evt.preventDefault();
		if (evt.targetTouches.length == 1) { // pause if multi-touch detected
			self.handleGraphInteractionStart(evt);
		}
		self.interact.isTouchEvent = true;
	}

	graphInteractTouchMove(evt) {
		evt.preventDefault();
		if (evt.targetTouches.length == 1) { // pause if multi-touch detected
			self.handleGraphInteractionMove(evt);
		}
	}

	graphInteractTouchEnd(evt){
		evt.preventDefault();
		if (evt.targetTouches && evt.targetTouches.length == 0) { // end only when all touches end
			if (self.interact.isDragging) {
				self.recalcRace();
			} else {
				self.handleGraphInteractionTap(evt);
			}
		}
	}

	graphInteractTouchCancel(evt) {
		evt.preventDefault();
		self.handleGraphInteractionCancel();
		self.interact.isTouchEvent = true;
	}
}