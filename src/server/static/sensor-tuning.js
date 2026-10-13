/* Additional receivers share RH's graph model without becoming race seats. */
$(document).ready(function () {
	'use strict';
	var container = $('#additional-sensor-tuning');
	if (!container.length) return;
	var providers = new Map();
	var alive = true;
	var pollTimer = null;
	var pollRequest = null;
	var writeGeneration = 0;
	var HISTORY_MS = 60000;

	function setLevels(card, enter, exit) {
		card.enter.val(enter);
		card.exit.val(exit);
		card.model.enter_at_level = enter;
		card.model.exit_at_level = exit;
		card.model.updateThresholds();
	}

	function controls(card) {
		card.controls.prop('disabled', !card.connected || card.busy);
		card.captures.toggle(card.canCapture).prop('disabled', !card.connected || card.busy || !card.frequency);
	}

	function restore(card) {
		card.dirty = false;
		setLevels(card, card.confirmedEnter, card.confirmedExit);
	}

	function write(card, suffix, data) {
		if (!card.connected || card.busy || card.removed) return;
		card.busy = true;
		writeGeneration++;
		controls(card);
		card.notice.text(__(suffix ? 'Capturing...' : 'Saving...'));
		card.request = $.ajax({
			url: '/sensor-tuning/' + encodeURIComponent(card.provider) + '/' + card.index + suffix,
			method: 'POST', contentType: 'application/json', data: JSON.stringify(data), timeout: 7500
		}).done(function (result) {
			if (card.removed) return;
			card.confirmedEnter = result.enter;
			card.confirmedExit = result.exit;
			restore(card);
			card.notice.text(__('Saved'));
		}).fail(function (xhr) {
			if (card.removed) return;
			restore(card);
			card.notice.text((xhr.responseJSON || {}).message || __('Unable to save receiver levels.'));
		}).always(function () {
			writeGeneration++;
			card.busy = false;
			card.request = null;
			if (!card.removed) controls(card);
		});
	}

	function save(card) {
		var enter = Number(card.enter.val()), exit = Number(card.exit.val());
		if (!card.enter.val() || !card.exit.val() || !Number.isInteger(enter) ||
				!Number.isInteger(exit) || exit < 0 || enter <= exit || enter > card.maxRssi) {
			restore(card);
			card.notice.text(__('EnterAt must be higher than ExitAt and within the RSSI range.'));
			return;
		}
		write(card, '', {enter: enter, exit: exit});
	}

	function removeNode(card) {
		card.removed = true;
		card.model.graph.stop();
		if (card.request) card.request.abort();
		card.element.remove();
	}

	function makeNode(provider, data) {
		var element = $('<div class="node">').appendTo(provider.nodesEl);
		$('<h3>').text(provider.label + ' - ' + __('Node') + ' ' + (data.index + 1)).appendTo(element);
		var channel = $('<div class="channel-block">').appendTo(element);
		var graph = $('<div class="rssi-graph">').css('touch-action', 'none').appendTo(element);
		var pause = $('<button type="button">').attr('title', __('Pause')).html(svg_asset.pause).appendTo(graph);
		var canvas = $('<canvas>').attr('aria-label', provider.label + ' RSSI ' + (data.index + 1)).appendTo(graph)[0];
		var crossing = $('<div class="crossing">').appendTo(element);
		var inputs = {}, nodeControls = $('<div class="node-controls">').appendTo(element);
		['enter', 'exit'].forEach(function (key) {
			var row = $('<div class="enter-exit-control">').appendTo(nodeControls);
			var id = 'sensor-' + provider.name + '-' + data.index + '-' + key;
			$('<label>').attr('for', id).text(__(key === 'enter' ? 'EnterAt' : 'ExitAt')).appendTo(row);
			inputs[key] = $('<input type="number" min="0">').attr({id: id, max: provider.maxRssi}).appendTo(row);
			$('<button type="button" class="sensor-capture">').attr('title', __('Capture current RSSI'))
				.text(__('Capture')).appendTo(row).on('click', function () { write(card, '/capture', {level: key}); });
		});
		var values = {}, table = $('<table>').appendTo(element);
		[['rssi', 'RSSI'], ['peak', 'NodePeak'], ['nadir', 'NodeNadir']].forEach(function (entry) {
			var row = $('<tr class="datarow">').appendTo(table);
			$('<td>').text(__(entry[1])).appendTo(row);
			values[entry[0]] = $('<td>').appendTo(row);
		});
		var card = {
			provider: provider.name, index: data.index, element: element, channel: channel,
			enter: inputs.enter, exit: inputs.exit, crossing: crossing, values: values,
			notice: $('<div role="status">').appendTo(element), controls: nodeControls.find('input, button'),
			captures: nodeControls.find('.sensor-capture'), model: new nodeModel(),
			maxRssi: provider.maxRssi, dirty: false, busy: false, connected: false, removed: false,
			confirmedEnter: data.enter, confirmedExit: data.exit
		};
		card.model.canvas = canvas;
		card.model.setup(canvas);
		setLevels(card, data.enter, data.exit);
		inputs.enter.add(inputs.exit).on('input', function () { card.dirty = true; }).on('change', function () { save(card); });
		pause.on('click', function () {
			var model = card.model;
			if (model.graphPaused) {
				model.graph.removeTimeSeries(model.pauseSeries);
				model.graph.removeTimeSeries(card.pauseCrossing);
				model.graph.addTimeSeries(model.series, rotorhazard.seriesStyle.rssi);
				model.graph.addTimeSeries(model.crossingSeries, rotorhazard.seriesStyle.crossing);
				model.graph.start();
			} else {
				model.graph.stop();
				model.graphPausedTime = Date.now();
				model.pauseSeries = new TimeSeries();
				card.pauseCrossing = new TimeSeries();
				model.pauseSeries.data = model.series.data.map(function (point) { return point.slice(); });
				card.pauseCrossing.data = model.crossingSeries.data.map(function (point) { return point.slice(); });
				model.graph.removeTimeSeries(model.series);
				model.graph.removeTimeSeries(model.crossingSeries);
				model.graph.addTimeSeries(model.pauseSeries, rotorhazard.seriesStyle.rssi);
				model.graph.addTimeSeries(card.pauseCrossing, rotorhazard.seriesStyle.crossing);
				model.graph.render(canvas, model.graphPausedTime);
			}
			model.graphPaused = !model.graphPaused;
			pause.html(model.graphPaused ? svg_asset.play : svg_asset.pause);
		});

		var dragging = null;
		function rssiAt(event) {
			var rect = canvas.getBoundingClientRect();
			var y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
			var model = card.model.graph;
			return Math.max(0, Math.min(card.maxRssi,
				Math.round(model.currentVisMinValue + (1 - y) * model.currentValueRange)));
		}
		canvas.addEventListener('pointerdown', function (event) {
			if (!card.connected || card.busy || event.button !== 0 || !canvas.clientHeight) return;
			var level = rssiAt(event);
			var key = Math.abs(level - card.model.enter_at_level) <= Math.abs(level - card.model.exit_at_level) ? 'enter' : 'exit';
			var tolerance = card.model.graph.currentValueRange * 12 / canvas.clientHeight;
			if (Math.abs(level - card.model[key + '_at_level']) > tolerance) return;
			dragging = key;
			canvas.setPointerCapture(event.pointerId);
			event.preventDefault();
		});
		canvas.addEventListener('pointermove', function (event) {
			if (!dragging) return;
			inputs[dragging].val(rssiAt(event));
			card.dirty = true;
			card.model.enter_at_level = Number(card.enter.val());
			card.model.exit_at_level = Number(card.exit.val());
			card.model.updateThresholds();
		});
		canvas.addEventListener('pointerup', function () {
			if (!dragging) return;
			dragging = null;
			save(card);
		});
		canvas.addEventListener('pointercancel', function () { dragging = null; restore(card); });
		provider.nodes.set(data.index, card);
		return card;
	}

	function update(data) {
		var seenProviders = new Set();
		data.providers.forEach(function (source) {
			seenProviders.add(source.name);
			var provider = providers.get(source.name);
			if (!provider) {
				var section = $('<section>').attr('data-sensor-provider', source.name).appendTo(container);
				$('<h3>').text(source.label).appendTo(section);
				provider = {name: source.name, label: source.label, maxRssi: source.max_rssi || 255,
					element: section, status: $('<p class="form-note">').appendTo(section),
					nodesEl: $('<div class="node-list">').appendTo(section), nodes: new Map()};
				providers.set(source.name, provider);
			}
			provider.label = source.label;
			provider.maxRssi = source.max_rssi || 255;
			provider.element.children('h3').text(source.label);
			provider.status.text((source.address ? source.address + ' - ' : '') +
				(source.connected ? __('Connected') : __('Disconnected')) + (source.message ? ': ' + source.message : ''));
			var seenNodes = new Set();
			source.nodes.forEach(function (node) {
				seenNodes.add(node.index);
				var card = provider.nodes.get(node.index) || makeNode(provider, node);
				card.connected = source.connected;
				card.element.children('h3').text(provider.label + ' - ' + __('Node') + ' ' + (node.index + 1));
				card.frequency = node.frequency;
				card.canCapture = source.can_capture;
				card.confirmedEnter = node.enter;
				card.confirmedExit = node.exit;
				card.maxRssi = source.max_rssi || 255;
				card.enter.add(card.exit).attr('max', card.maxRssi);
				controls(card);
				card.channel.text(node.frequency ? node.frequency + ' MHz' : __('Disabled'));
				card.crossing.toggleClass('is-crossing', source.connected && node.inside)
					.text(!source.connected ? __('Disconnected') : node.inside ? __('Crossing') : __('Clear'));
				Object.keys(card.values).forEach(function (key) { card.values[key].text(source.connected ? node[key] : '-'); });
				if (!card.dirty && !card.busy && !card.controls.is(':focus')) setLevels(card, node.enter, node.exit);
				if (!source.connected) return;
				var model = card.model;
				if (!card.dirty && !model.graphPaused) {
					model.graph.options.maxValue = Math.max(node.rssi, node.peak + 1, node.enter + 10);
					model.graph.options.minValue = Math.max(0, Math.min(node.rssi, node.nadir - 1, node.exit - 10));
				}
				var now = Date.now();
				model.series.append(now, node.frequency ? node.rssi : 0);
				model.crossingSeries.append(now, node.inside ? card.maxRssi * 2 : -10);
				// Detached paused series are not pruned by Smoothie's renderer.
				model.series.dropOldData(now - HISTORY_MS, 2);
				model.crossingSeries.dropOldData(now - HISTORY_MS, 2);
			});
			provider.nodes.forEach(function (card, index) {
				if (!seenNodes.has(index)) { removeNode(card); provider.nodes.delete(index); }
			});
		});
		providers.forEach(function (provider, name) {
			if (!seenProviders.has(name)) {
				provider.nodes.forEach(removeNode);
				provider.element.remove();
				providers.delete(name);
			}
		});
	}

	function poll() {
		if (!alive || pollRequest) return;
		var generation = writeGeneration;
		pollRequest = $.ajax({url: '/sensor-tuning/data', dataType: 'json', cache: false, timeout: 5000})
			.done(function (data) { if (generation === writeGeneration) update(data); })
			.fail(function () {
				providers.forEach(function (provider) {
					provider.status.text(__('Unable to read receiver data.'));
					provider.nodes.forEach(function (card) {
						card.connected = false;
						controls(card);
						card.crossing.removeClass('is-crossing').text(__('Disconnected'));
					});
				});
			}).always(function () {
				pollRequest = null;
				if (alive) pollTimer = window.setTimeout(poll, 250);
			});
	}
	window.addEventListener('pagehide', function () {
		alive = false;
		window.clearTimeout(pollTimer);
		if (pollRequest) pollRequest.abort();
		providers.forEach(function (provider) {
			provider.nodes.forEach(function (card) { card.model.graph.stop(); });
		});
	});
	window.addEventListener('pageshow', function () {
		if (alive) return;
		alive = true;
		providers.forEach(function (provider) {
			provider.nodes.forEach(function (card) { if (!card.model.graphPaused) card.model.graph.start(); });
		});
		poll();
	});
	poll();
});
