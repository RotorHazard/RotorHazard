/* Marshaling functions */

const MARSHAL_TYPE = {
	RSSI: 0,
	HYBRID_PASS_PEAK: 1, // not implemented
	PASS_PEAK_ONLY: 2,
};

class RHMarshal {
	self = false;

	elements = {
		graph_canvas_id: false,
		graph_canvas: false,
	}

	time_format = null;
	start_thresh_lower_amount = 0;
	start_thresh_lower_duration = 0;
	min_lap_ms = 0;
	min_lap_behavior = null;
	min_first_crossing_ms = 0;

	callbacks = {
		calcLaps: false,
		calibration: false,
		clearMarkedLap: false,
		displayLaps: false,
		graphInteractCancel: false,
		graphInteractTap: false,
		recalcRace: false,
		viewRange: false,
	}

	race = {
		history_times: null,
		history_values: null,
		marshal_type: MARSHAL_TYPE.RSSI,
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

	// visible x-range of the graph in seconds from race start; null = full race
	view = {
		from: null,
		to: null,
	}
	min_view_span = 0.1; // seconds

	seriesStyle = {
		rssi: {lineWidth:1.7,
			strokeStyle:'hsl(214, 53%, 60%)',
			fillStyle:'hsla(214, 53%, 60%, 0.4)'
		},
		lap_marker: {
			lineWidth: 1.7,
			strokeStyle:'none',
			fillStyle:'hsla(136, 71%, 70%, 0.3)'
		},
		deleted_lap: {
			lineWidth: 1.7,
			strokeStyle:'none',
			fillStyle:'hsla(8.2, 86.5%, 53.7%, 0.2)'
		},
		selection: {
			lineWidth: 1.7,
			strokeStyle:'hsl(70, 60%, 60%)',
			lineWidth: 3
		},
		race_bounds: {
			strokeStyle:'none',
			fillStyle:'hsla(0, 0%, 100%, 0.15)'
		}
	}

	// interactions
	interact = {
		canDrag: false,
		isDragging: false,
		startingEnter: false,
		startingExit: false,
		startingX: false,
		startingY: false,
		startingClientX: 0,
		startingClientY: 0,
		startingView: null,
		dragAxis: null, // 'x' scrolls the graph, 'y' adjusts EnterAt/ExitAt
		isPanning: false,
		adjustEnter: true,
		isTouchEvent: false,
	}
	drag_threshold_px = 3;
	wheel_guard_until = 0;
	wheel_guard_ms = 300;
	wheel_guard_scroll = null;

	constructor(options) {
		self = this;
		self.elements.graph_canvas_id = options.elements.graph_canvas_id;
		self.time_format = options.time_format;
		self.start_thresh_lower_amount = options.start_thresh_lower_amount
		self.start_thresh_lower_duration = options.start_thresh_lower_duration;
		self.min_lap_ms = options.min_lap_ms
		self.min_lap_behavior = options.min_lap_behavior
		self.min_first_crossing_ms = options.min_first_crossing_ms
		self.callbacks.calcLaps = options.callbacks.calcLaps;
		self.callbacks.calibration = options.callbacks.calibration;
		self.callbacks.clearMarkedLap = options.callbacks.clearMarkedLap;
		self.callbacks.displayLaps = options.callbacks.displayLaps;
		self.callbacks.graphInteractCancel = options.callbacks.graphInteractCancel;
		self.callbacks.graphInteractTap = options.callbacks.graphInteractTap;
		self.callbacks.recalcRace = options.callbacks.recalcRace;
		self.callbacks.viewRange = options.callbacks.viewRange;

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
		// a drag started on the graph continues outside it until the button is released
		$(self.elements.graph_canvas).on('mousedown', self.graphInteractMouseDown);
		$(document).on('mousemove', self.graphInteractMouseMove);
		$(document).on('mouseup', self.graphInteractMouseUp);

		// touch handlers
		$(self.elements.graph_canvas).on('touchstart', self.graphInteractTouchStart);
		$(self.elements.graph_canvas).on('touchmove', self.graphInteractTouchMove);
		$(self.elements.graph_canvas).on('touchend', self.graphInteractTouchEnd);
		$(self.elements.graph_canvas).on('touchCancel', self.graphInteractTouchCancel);
		$(document).on('touchend', self.graphInteractCancel);

		// zoom with the mouse wheel; the page is held at its scroll position during and briefly
		//  after a zoom gesture, as some browsers scroll it even though the wheel events are prevented
		self.elements.graph_canvas.addEventListener('wheel', self.graphInteractWheel, {passive: false});
		window.addEventListener('scroll', self.graphScrollGuard, {passive: true});

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
			scaleSmoothing: 1,
			nonRealtimeData: true,
			maxDataSetLength: Infinity, // keep data scrolled off the left edge when zoomed in
		});
		self.graph_series.rssi = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.rssi, this.seriesStyle.rssi);
		self.graph_series.lap_marker = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.lap_marker, this.seriesStyle.lap_marker);
		self.graph_series.deleted_lap = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.deleted_lap, this.seriesStyle.deleted_lap);
		self.graph_series.selection = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.selection, this.seriesStyle.selection);
		self.graph_series.race_bounds = new TimeSeries();
		self.graph.addTimeSeries(self.graph_series.race_bounds, this.seriesStyle.race_bounds);

		self.graph.streamTo(self.elements.graph_canvas, 0);
		self.graph.stop();
	}

	setRaceData(args) {
		self.race.calc_result = {};
		// fill current data with race meta
		self.race.round_id = args.round;
		self.race.heat_id = args.heat;
		self.race.race_id = args.race_id;
		self.race.class_id = args.class_id;
		self.race.race_format = args.race_format;
		self.race.start_time = args.start_time;
		self.race.start_time_formatted = args.start_time_formatted;
	}

	setPilotData(args) {
		self.race.laps = args.laps;
		self.race.enter_at = args.enter_at;
		self.race.exit_at = args.exit_at;
		self.race.marshal_type = args.marshal_type;

		self.race.pilotrace_id = args?.pilotrace_id;
		self.race.pilot_id = args?.pilot_id;
		self.race.seat = args?.seat;
		self.race.callsign = args?.callsign;

		self.setHistory({
			'history_times': args.history_times,
			'history_values': args.history_values
		});
	}

	setHistory(args) {
		if (self.race.marshal_type == MARSHAL_TYPE.PASS_PEAK_ONLY) {
			var times = [];
			var values = [];
			times.push(0);
			values.push(0);
			for (var i in self.race.laps) {
				var lap = self.race.laps[i];
				times.push(self.race.start_time + (lap.lap_time_stamp / 1000));
				values.push(lap.peak_rssi);
				times.push(self.race.start_time + (lap.lap_time_stamp + 1) / 1000);
				values.push(0);
			}
			times.push(times[times.length - 1] + 10);
			values.push(0);

			self.race.history_times = times;
			self.race.history_values = values;
		} else {
			self.race.history_times = args.history_times;
			self.race.history_values = args.history_values;
		}
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
		self.view.from = null;
		self.view.to = null;
		self.notifyViewRange();

		if (!self.race.race_format) {
			self.race.race_format = {
				unlimited_time: true,
				race_time_sec: null,
				start_delay_max: 0
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
		self.graph_series.race_bounds.clear();
		self.graph_series.race_bounds.data = [];

		if (self.min_first_crossing_ms) {
			self.graph_series.race_bounds.append(0, self.graph.options.maxValue + 10);
			self.graph_series.race_bounds.append(self.min_first_crossing_ms/1000 - .001, self.graph.options.maxValue + 10);
			self.graph_series.race_bounds.append(self.min_first_crossing_ms/1000, self.graph.options.minValue - 10);
		} else {
			self.graph_series.race_bounds.append(0, self.graph.options.minValue - 10);
		}

		if (self.race.race_format.race_time_sec) {
			// convert lap time to history time
			var finish_time = self.race.race_format.race_time_sec;
			// highlight after finish
			self.graph_series.race_bounds.append(finish_time - .001, self.graph.options.minValue - 10);
			self.graph_series.race_bounds.append(finish_time, self.graph.options.maxValue + 10);
			self.graph_series.race_bounds.append(self.race.history_duration + .001, self.graph.options.maxValue + 10);
		}

		// Lap marker series lines drawn below the bottom of the graph
		self.clearCrossings();
		self.clearMarkedLap();
		self.renderGraph();

		// populate laps
		self.displayLaps();
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
				seat: self.race.seat,
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
				seat: self.race.seat,
			});
		}
		self.refreshDisplay();
	}

	loadEnterExit(enter, exit) {
		// applies a valid loaded pair unclamped, as saved values are on first display; returns whether it was applied
		if (!Number.isInteger(enter) || !Number.isInteger(exit) || enter <= exit) {
			return false;
		}
		self.applyEnterExit(enter, exit);
		return true;
	}

	setEnterExit(enter, exit) {
		enter = Math.min(Math.max(enter, self.graph.options.minValue), self.graph.options.maxValue);
		exit = Math.min(Math.max(exit, self.graph.options.minValue), self.graph.options.maxValue);
		if (exit > enter) {
			exit = enter;
		}
		self.applyEnterExit(enter, exit);
	}

	applyEnterExit(enter, exit) {
		if (enter == self.race.enter_at && exit == self.race.exit_at) {
			return;
		}
		self.race.enter_at = enter;
		self.race.exit_at = exit;
		if (typeof self.callbacks.calibration === 'function') {
			self.callbacks.calibration({
				enter: self.race.enter_at,
				exit: self.race.exit_at,
				seat: self.race.seat,
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

		// keep the marked lap visible when zoomed in
		var range = self.getViewRange();
		if (self.isZoomed() && (history_time_stamp < range.from || history_time_stamp > range.to)) {
			var half = (range.to - range.from) / 2;
			self.setViewRange(history_time_stamp - half, history_time_stamp + half, false);
		}
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
		var range = self.getViewRange();
		var span = (range.to - range.from) / graphWidth;

		self.graph.options.millisPerPixel = span;
		self.graph.options.horizontalLines = [
			{color:'hsl(8.2, 86.5%, 53.7%)', lineWidth:1.7, value: self.race.enter_at}, // red
			{color:'hsl(25, 85%, 55%)', lineWidth:1.7, value: self.race.exit_at}, // orange
		];

		self.graph.lastChartTimestamp = 0;  // page renders on demand, so never let smoothie skip a paint as "same frame"
		self.graph.render(self.elements.graph_canvas, range.to);
	}

	getViewRange() {
		var duration = self.race.history_duration || 0;
		return {
			from: (self.view.from === null) ? 0 : self.view.from,
			to: (self.view.to === null) ? duration : self.view.to,
			duration: duration,
		};
	}

	isZoomed() {
		return self.view.from !== null;
	}

	canZoom() {
		// wheel zoom and drag scrolling only where the page shows the zoom controls
		return typeof self.callbacks.viewRange === 'function';
	}

	setViewRange(from, to, render=true) {
		// show only the given range (seconds from race start) across the graph width
		var duration = self.race.history_duration || 0;
		from = Number(from);
		to = Number(to);
		if (!self.race_loaded || !isFinite(from) || !isFinite(to) || duration <= 0) {
			return false;
		}
		if (to < from) {
			[from, to] = [to, from];
		}
		var minSpan = Math.min(self.min_view_span, duration);
		if (to - from < minSpan) {
			var mid = (from + to) / 2;
			from = mid - minSpan / 2;
			to = mid + minSpan / 2;
		}
		// shift (not shrink) a range that runs past either end
		if (from < 0) {
			to -= from;
			from = 0;
		}
		if (to > duration) {
			from -= to - duration;
			to = duration;
		}
		from = Math.max(from, 0);

		if (from <= 0 && to >= duration) {
			self.view.from = null;
			self.view.to = null;
		} else {
			self.view.from = from;
			self.view.to = to;
		}
		self.notifyViewRange();
		if (render) {
			self.renderGraph();
		}
		return true;
	}

	resetViewRange() {
		self.view.from = null;
		self.view.to = null;
		self.notifyViewRange();
		if (self.race_loaded) {
			self.renderGraph();
		}
	}

	zoomViewRange(factor, anchor=0.5) {
		// factor < 1 zooms in, > 1 zooms out; anchor is the graph x-fraction kept in place
		var range = self.getViewRange();
		var span = range.to - range.from;
		var at = range.from + span * anchor;
		var newSpan = span * factor;
		self.setViewRange(at - newSpan * anchor, at + newSpan * (1 - anchor));
	}

	panViewRange(fraction) {
		// moves the view by a fraction of its width (negative = left)
		if (!self.isZoomed()) {
			return;
		}
		var range = self.getViewRange();
		var shift = (range.to - range.from) * fraction;
		self.setViewRange(range.from + shift, range.to + shift);
	}

	notifyViewRange() {
		if (typeof self.callbacks.viewRange === 'function') {
			var range = self.getViewRange();
			range.zoomed = self.isZoomed();
			self.callbacks.viewRange(range);
		}
	}

	clearGraph(){
		self.context.clearRect(0, 0, self.elements.graph_canvas.width, self.elements.graph_canvas.height);
	}

	processRXData() {
		var last_lap_time_stamp = -Infinity;
		var laps = [];
		if (self.race.marshal_type == MARSHAL_TYPE.PASS_PEAK_ONLY || self.race.marshal_type == MARSHAL_TYPE.HYBRID_PASS_PEAK) {
			for (var lap_i in self.race.laps) {
				var lap = self.race.laps[lap_i];
				lap.source = 2;
				lap.crossingStart = lap.lap_time_stamp;
				lap.crossingEnd = lap.lap_time_stamp + 1;

				if (lap.lap_time_stamp < self.min_first_crossing_ms) {
					lap.deleted = true;
				} else if (lap.peak_rssi < self.race.enter_at) {
					lap.deleted = true;
				} else {
					lap.deleted = false;
				}

				if (self.min_lap_behavior && lap_time_stamp < last_lap_time_stamp + self.min_lap) {
					lapdata.deleted = true;
				} else {
					last_lap_time_stamp = lap_time_stamp;
				}
				laps.push();
			}
		} else {
			var crossing = false;
			var crossingStart = 0;
			var crossingEnd = 0;
			var peakRssi = 0;
			var peakFirst = 0;
			var peakLast = 0;
			var startThreshLowerFlag = false;

			var localEnter = self.race.enter_at
			var localExit = self.race.exit_at

			// set lower EnterAt/ExitAt values at race start if configured
			if (self.start_thresh_lower_amount > 0 && self.start_thresh_lower_duration > 0) {
				var diffVal = (self.race.enter_at - self.race.exit_at) * self.start_thresh_lower_amount / 100;
				if (diffVal > 0) {
					localEnter = self.race.enter_at - diffVal;
					localExit = self.race.exit_at - diffVal;
					startThreshLowerFlag = true;
				}
			}

			for(var idx in self.race.history_values) {
				var rssi = self.race.history_values[idx];
				var time = self.race.history_times[idx];

				if (startThreshLowerFlag) {
					// if initial pass recorded or past duration then restore EnterAt/ExitAt values
					if (laps.length > 0 || time >= self.race.start_time + self.start_thresh_lower_duration + self.race.race_format.start_delay_max) {
						localEnter = self.race.enter_at;
						localExit = self.race.exit_at;
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
								peak_rssi: peakRssi,
								deleted: false
							};
							if (lap_time_stamp < self.min_first_crossing_ms) {
								lapdata.deleted = true;
							} else if (self.min_lap_behavior && lap_time_stamp < last_lap_time_stamp + self.min_lap_ms) {
								lapdata.deleted = true;
							} else {
								last_lap_time_stamp = lap_time_stamp;
							}
							laps.push(lapdata);
						}
						crossing = false;
						peakRssi = 0;
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
		if (self.race_loaded) {
			if (!self.race.marshal_type || self.race.marshal_type == MARSHAL_TYPE.RSSI) {
				var laps = self.race.calc_result;
				for (var lap_i in self.race.laps) {
					var lap = self.race.laps[lap_i];
					if (lap.source == 1 || lap.source == 4) { // LapSource.MANUAL = 1, LapSource.API = 4
						laps.push(lap);
					}
				}
				self.race.laps = laps;
			}
			self.updateIncrementalLapTimes();
			self.displayLaps();
			self.renderGraph();
		}
		if (typeof self.callbacks.recalcRace === 'function') {
			self.callbacks.recalcRace(self.race_loaded);
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
		self.displayLaps();
		self.renderGraph();
		return true;
	}

	markLapDeleted(lap_index) {
		self.race.laps[lap_index].deleted = true;
		self.clearMarkedLap();
		self.updateIncrementalLapTimes();
		self.displayLaps(lap_index);
		self.renderGraph();
	}

	restoreDeletedLap(lap_index) {
		self.race.laps[lap_index].deleted = false;
		self.updateIncrementalLapTimes();
		self.displayLaps(lap_index);
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
		self.displayLaps();
		self.renderGraph();
		return true;
	}

	getRaceData() {
		if (!self.race_loaded) {
			return false;
		}

		var data = {
			heat_id: self.race.heat_id,
			round_id: self.race.round_id,
			callsign: self.race.callsign,
			race_id: self.race.race_id,
			pilotrace_id: self.race.pilotrace_id,
			seat: self.race.seat,
			pilot_id: self.race.pilot_id,
			laps: self.race.laps,
			enter_at: self.race.enter_at,
			exit_at: self.race.exit_at,
		}

		return data;
	}

	displayLaps(marked_lap=null) {
		self.clearCrossings();
		if (typeof self.callbacks.displayLaps === 'function') {
			self.callbacks.displayLaps(self.race.laps, marked_lap);
		}
	}

	mapRange(val, start, end){
		return val * (end - start) / 1 + start;
	}

	handleGraphInteractionStart(evt) {
		var rect = self.graph.canvas.getBoundingClientRect();

		if (evt.targetTouches) {
			var clientX = evt.targetTouches[0].clientX;
			var clientY = evt.targetTouches[0].clientY;
		} else {
			var clientX = evt.clientX;
			var clientY = evt.clientY;
		}
		var x = (clientX - rect.x) / rect.width;
		var y = (clientY - rect.y) / rect.height;

		var rssi = parseInt(self.mapRange(y, self.graph.options.maxValue, self.graph.options.minValue));

		self.interact.startingEnter = self.race.enter_at;
		self.interact.startingExit = self.race.exit_at;
		self.interact.startingX = x;
		self.interact.startingY = y;
		self.interact.startingClientX = clientX;
		self.interact.startingClientY = clientY;
		self.interact.startingView = self.getViewRange();
		self.interact.dragAxis = null;
		self.interact.isDragging = false;
		self.interact.isPanning = false;

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
		// user drags on graph: up/down adjusts EnterAt/ExitAt, left/right scrolls a zoomed graph
		var rect = self.graph.canvas.getBoundingClientRect();

		if (evt.targetTouches) {
			var clientX = evt.targetTouches[0].clientX;
			var clientY = evt.targetTouches[0].clientY;
		} else {
			var clientX = evt.clientX;
			var clientY = evt.clientY;
		}

		if (!self.interact.dragAxis) {
			var dx = Math.abs(clientX - self.interact.startingClientX);
			var dy = Math.abs(clientY - self.interact.startingClientY);
			if (self.canZoom() && dx >= self.drag_threshold_px && dx > dy) {
				self.interact.dragAxis = 'x';
			} else if (dy >= self.drag_threshold_px) {
				self.interact.dragAxis = 'y';
			} else { // prevent accidental drag
				return;
			}
		}

		if (self.interact.dragAxis == 'x') {
			self.interact.isPanning = true;
			if (self.isZoomed()) {
				var view = self.interact.startingView;
				var shift = (self.interact.startingClientX - clientX) / rect.width * (view.to - view.from);
				self.setViewRange(view.from + shift, view.to + shift);
			}
		} else {
			self.interact.isDragging = true;

			var y = (clientY - rect.top) / rect.height;
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
		var range = self.getViewRange();
		var time = self.race.start_time + self.mapRange(self.interact.startingX, range.from, range.to);

		if (!$.isEmptyObject(self.race.calc_result)) {
			// find closest start/end time to "time" point
			var delta = Infinity;
			var selectedLap = null;
			for (var i in self.race.calc_result) {
				var lap = self.race.calc_result[i];

				if (time > lap.crossingEnd) {
					selectedLap = i;
					delta = Math.abs(time - lap.crossingEnd);
				} else if (time >= lap.crossingStart
					&& time <= lap.crossingEnd) {
					selectedLap = i;
					break;
				} else {
					var diff = Math.abs(time - lap.crossingStart);
					if (diff < delta) {
						selectedLap = i;
					}
					break;
				}
			}

			if (typeof self.callbacks.graphInteractTap === 'function') {
				self.callbacks.graphInteractTap({
					'lapTimeStamp': self.race.calc_result[selectedLap].lap_time_stamp,
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

	graphInteractCancel() {
		if (self.interact.canDrag) {
			var wasPanning = self.interact.isPanning;
			self.endGraphInteraction();
			if (!wasPanning) {
				self.handleGraphInteractionCancel();
			}
		}
	}

	endGraphInteraction() {
		self.interact.canDrag = false;
		self.interact.isDragging = false;
		self.interact.isPanning = false;
		self.interact.dragAxis = null;
	}

	// mouse handlers
	graphInteractMouseDown(evt) {
		if (!self.interact.isTouchEvent && evt.button === 0) { // left button only
			evt.preventDefault(); // no text selection while dragging
			self.interact.canDrag = true;
			self.handleGraphInteractionStart(evt);
		}
	}

	graphInteractMouseMove(evt) {
		if (!self.interact.isTouchEvent) {
			if (self.interact.canDrag) {
				self.handleGraphInteractionMove(evt);
				if (self.interact.isDragging) {
					self.recalcRace();
				}
			}
		}
	}

	graphInteractMouseUp(evt){
		if (evt.button !== 0) {
			return;
		}
		if (!self.interact.isTouchEvent && self.interact.canDrag) {
			if (self.interact.isPanning) {
				// scrolling only; no tap or lap recalculation
			} else if (self.interact.isDragging) {
				self.recalcRace();
			} else {
				self.handleGraphInteractionTap(evt);
			}
			self.endGraphInteraction();
		}
		self.interact.isTouchEvent = false;
	}

	graphInteractWheel(evt) {
		if (!self.race_loaded || !self.canZoom()) {
			return;
		}
		var e = evt.originalEvent || evt;
		evt.preventDefault();
		var now = performance.now();
		if (now >= self.wheel_guard_until) { // gesture start: hold the page here
			self.wheel_guard_scroll = {x: window.scrollX, y: window.scrollY};
		}
		self.wheel_guard_until = now + self.wheel_guard_ms;
		if (!e.deltaY) {
			return;
		}
		var rect = self.elements.graph_canvas.getBoundingClientRect();
		var anchor = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
		// zoom by wheel distance (a wheel notch is about 100 px) so trackpads zoom smoothly
		var px = e.deltaY * (e.deltaMode == 1 ? 33 : (e.deltaMode == 2 ? 400 : 1));
		px = Math.max(Math.min(px, 300), -300);
		self.zoomViewRange(Math.pow(1.25, px / 100), anchor);
	}

	graphScrollGuard() {
		// undoes page scrolling while a graph zoom gesture is still arriving
		var held = self.wheel_guard_scroll;
		if (held && performance.now() < self.wheel_guard_until
			&& (window.scrollX != held.x || window.scrollY != held.y)) {
			window.scrollTo({left: held.x, top: held.y, behavior: 'instant'});
		}
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
			if (self.interact.isPanning) {
				// scrolling only; no tap or lap recalculation
			} else if (self.interact.isDragging) {
				self.recalcRace();
			} else {
				self.handleGraphInteractionTap(evt);
			}
			self.interact.isDragging = false;
			self.interact.isPanning = false;
			self.interact.dragAxis = null;
		}
		evt.stopPropagation();
	}

	graphInteractTouchCancel(evt) {
		evt.preventDefault();
		self.handleGraphInteractionCancel();
		self.interact.isTouchEvent = true;
	}
}