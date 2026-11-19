
var rhui = {
	_formatRangeValue: function (settings, field, value) {
		var htmlAttributes = settings.html_attributes || {};
		var prefix = htmlAttributes.value_prefix != null
			? htmlAttributes.value_prefix
			: field.attr('data-value-prefix') || '';
		var suffix = htmlAttributes.value_suffix != null
			? htmlAttributes.value_suffix
			: field.attr('data-value-suffix') || '';
		var decimals = htmlAttributes.value_decimals != null
			? htmlAttributes.value_decimals
			: field.attr('data-value-decimals');
		if (decimals != null && value !== '' && !isNaN(value)) {
			value = Number(value).toFixed(parseInt(decimals, 10));
		}
		return prefix + value + suffix;
	},
	_updateRangeValue: function (field, settings, value) {
		settings = settings || field.data('rhui-range-settings') || {};
		if (value == null) {
			value = field.val();
		}
		field.closest('.uifield-range').find('output.uifield-range-value')
			.text(this._formatRangeValue(settings, field, value));
	},
	updateRangeValue: function (field, value) {
		this._updateRangeValue(field, null, value);
	},
	_bindRangeValue: function (field, settings) {
		field.data('rhui-range-settings', settings || {});
		if (!field.data('rhui-range-bound')) {
			var rhuiObj = this;
			field.on('input change', function () {
				rhuiObj.updateRangeValue($(this));
			});
			field.data('rhui-range-bound', true);
		}
	},
	_modelField: function (field_options) {
		var settings = {
			data: {},
			desc: null,
			html_attributes: {},
			fieldClass: null,
			field_type: null,
			genericOption: null,
			id: null,
			label: null,
			options: null,
			placeholder: null,
			value: null,
			wrapperEl: null,
			wrapperClass: null
		}

		for (item in settings) {
			if (field_options[item] != null) {
				settings[item] = field_options[item];
			}
		}

		return settings;
	},
	buildField: function(field_options) {
		var settings = this._modelField(field_options);

		if (settings.wrapperEl) {
			var wrapper = $('<' + settings.wrapperEl + '>');
		} else {
			var wrapper = $('<div>');
		}

		if (!settings.id) {
			settings.id = 'setting_' + window.performance.now()
		}

		if (settings.wrapperClass) {
			wrapper.addClass(settings.wrapperClass);
		}

		var labelWrap = $('<div class="label-block"></div>');

		var label = $('<label>')
			.attr('for', settings.id)
			.text(__(settings.label));

		labelWrap.append(label);

		if (settings.desc) {
			labelWrap.append('<p class="desc">' + settings.desc + '</p>');
		}

		if (settings.field_type == 'text') {
			var field = $('<input>')
				.attr('type', 'text')
				.attr('placeholder', settings.placeholder);
			if ('minlength' in settings.html_attributes) {
				field.attr('minlength', settings.html_attributes.minlength)
			}
			if ('maxlength' in settings.html_attributes) {
				field.attr('maxlength', settings.html_attributes.maxlength)
			}
			if ('pattern' in settings.html_attributes) {
				field.attr('pattern', settings.html_attributes.pattern)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'password') {
			var field = $('<input>')
				.attr('type', 'text')
				.addClass('uifield-password')
				.attr('placeholder', settings.placeholder);
			if ('minlength' in settings.html_attributes) {
				field.attr('minlength', settings.html_attributes.minlength)
			}
			if ('maxlength' in settings.html_attributes) {
				field.attr('maxlength', settings.html_attributes.maxlength)
			}
			if ('pattern' in settings.html_attributes) {
				field.attr('pattern', settings.html_attributes.pattern)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'basic_int') {
			var field = $('<input>')
				.attr('type', 'number')
				.attr('min', 0)
				.attr('max', 999)
				.attr('step', 1)
				.attr('placeholder', settings.placeholder);
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'number') {
			var field = $('<input>')
				.attr('type', 'number')
				.attr('placeholder', settings.placeholder);

			if ('min' in settings.html_attributes) {
				field.attr('min', settings.html_attributes.min)
			}
			if ('max' in settings.html_attributes) {
				field.attr('max', settings.html_attributes.max)
			}
			if ('step' in settings.html_attributes) {
				field.attr('step', settings.html_attributes.step)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'range') {
			var field = $('<input>')
				.attr('type', 'range')
				.attr('placeholder', settings.placeholder);
			var rangeWrap = $('<div>')
				.addClass('uifield-range');
			var valueEl = $('<output>')
				.addClass('uifield-range-value')
				.attr('for', settings.id);
			this._bindRangeValue(field, settings);

			if ('min' in settings.html_attributes) {
				field.attr('min', settings.html_attributes.min)
			}
			if ('max' in settings.html_attributes) {
				field.attr('max', settings.html_attributes.max)
			}
			if ('step' in settings.html_attributes) {
				field.attr('step', settings.html_attributes.step)
			}
			wrapper.append(labelWrap);
			rangeWrap.append(field);
			rangeWrap.append(valueEl);
			wrapper.append(rangeWrap);
		} else if (settings.field_type == 'select') {
			var field = $('<select>')

			for (var opt_id in settings.options) {
				var opt = settings.options[opt_id];

				var opt_el = $('<option>')
					.attr('value', opt.value)
					.text(opt.label);
				field.append(opt_el);
			}
			if (!settings.value && settings.options && settings.options.length) {
				settings.value = settings.options[0].value;
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'status') {
			var field = $('<output>')
				.addClass('uifield-status');
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'checkbox') {
			var field = $('<input>')
				.attr('type', 'checkbox')
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'date') {
			var field = $('<input>')
				.attr('type', 'date')

			if ('min' in settings.html_attributes) {
				field.attr('min', settings.html_attributes.min)
			}
			if ('max' in settings.html_attributes) {
				field.attr('max', settings.html_attributes.max)
			}
			if ('step' in settings.html_attributes) {
				field.attr('step', settings.html_attributes.step)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'time') {
			var field = $('<input>')
				.attr('type', 'time')

			if ('min' in settings.html_attributes) {
				field.attr('min', settings.html_attributes.min)
			}
			if ('max' in settings.html_attributes) {
				field.attr('max', settings.html_attributes.max)
			}
			if ('step' in settings.html_attributes) {
				field.attr('step', settings.html_attributes.step)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'datetime') {
			var field = $('<input>')
				.attr('type', 'datetime-local')

			if ('min' in settings.html_attributes) {
				field.attr('min', settings.html_attributes.min)
			}
			if ('max' in settings.html_attributes) {
				field.attr('max', settings.html_attributes.max)
			}
			if ('step' in settings.html_attributes) {
				field.attr('step', settings.html_attributes.step)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'email') {
			var field = $('<input>')
				.attr('type', 'email')
				.attr('placeholder', settings.placeholder);

			if ('minlength' in settings.html_attributes) {
				field.attr('minlength', settings.html_attributes.minlength)
			}
			if ('maxlength' in settings.html_attributes) {
				field.attr('maxlength', settings.html_attributes.maxlength)
			}
			if ('pattern' in settings.html_attributes) {
				field.attr('pattern', settings.html_attributes.pattern)
			}
			if ('multiple' in settings.html_attributes) {
				field.prop('multiple', true);
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'tel') {
			var field = $('<input>')
				.attr('type', 'tel')
			if ('minlength' in settings.html_attributes) {
				field.attr('minlength', settings.html_attributes.minlength)
			}
			if ('maxlength' in settings.html_attributes) {
				field.attr('maxlength', settings.html_attributes.maxlength)
			}
			if ('pattern' in settings.html_attributes) {
				field.attr('pattern', settings.html_attributes.pattern)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.field_type == 'url') {
			var field = $('<input>')
				.attr('type', 'url')
			if ('minlength' in settings.html_attributes) {
				field.attr('minlength', settings.html_attributes.minlength)
			}
			if ('maxlength' in settings.html_attributes) {
				field.attr('maxlength', settings.html_attributes.maxlength)
			}
			if ('pattern' in settings.html_attributes) {
				field.attr('pattern', settings.html_attributes.pattern)
			}
			wrapper.append(labelWrap);
			wrapper.append(field);
		} else {
			console.log('fieldtype not supported');
			return false;
		}

		field.addClass(settings.fieldClass)
			.attr('id', settings.id)

		if (settings.genericOption) {
			field.addClass('set-option')
				.data('option', settings.genericOption)
		}

		for (var idx in settings.data) {
			field.data(idx, settings.data[idx])
		}

		this.updateField(field_options, field);
		return wrapper
	},
	updateField: function(field_options, element) {
		var settings = this._modelField(field_options);

		if (settings.field_type == 'checkbox') {
			element.prop('checked', settings.value);
		} else if (settings.field_type == 'status') {
			element.text(settings.value == null ? '' : settings.value);
		} else {
			element.val(settings.value);
		}
		if (settings.field_type == 'range') {
			this._updateRangeValue(element, settings);
		}

		for (var idx in settings.data) {
			element.data(idx, settings.data[idx])
		}
	},
	getFieldVal: function(element) {
		var el = $(element);
		var field = el.data('field');

		if (el.attr('type') == 'checkbox') {
			value = el.prop('checked');
		} else {
			value = el.val();
		}

		return value;
	},
	_markdownConverter: null,
	markdownToHtml: function(text) {
		if (!this._markdownConverter) {
			this._markdownConverter = new showdown.Converter({
				ghCodeBlocks: true,
				ghCompatibleHeaderId: true,
				literalMidWordUnderscores: true,
				simpleLineBreaks: true,
				headerLevelStart: 3
			});
		}
		return this._markdownConverter.makeHtml(text);
	},
	buildPanels: function(msg, page) {
		// builds the plugin panels of a 'ui' message for this page
		this.listenPanelUpdates(page);
		if (msg.page != page) {
			return;
		}
		if (msg.replace_panels !== false) {
			$('#custom-ui').empty();
		}

		for (var i in msg.panels) {
			var panel = msg.panels[i];

			if (msg.replace_panels === false) {
				var panel_el = $('#ui-custom-' + panel.panel.name);
				var panel_content_el = panel_el.children('.panel-content');
				panel_content_el.empty();
			} else {
				var panel_el = $('<div class="panel collapsing active">');
				panel_el.attr('id', 'ui-custom-' + panel.panel.name);
				var panel_header_el = $('<div class="panel-header">');
				panel_header_el.append('<h2><button class="no-style">' + panel.panel.label + '</button></h2>');
				var panel_content_el = $('<div class="panel-content">');
				panel_el.append(panel_header_el);

				// panel open/close
				if (panel.panel.open) {
					panel_el.addClass('open');
					panel_content_el.show();
				} else {
					panel_el.removeClass('open');
					panel_content_el.hide();
				}
			}

			// add markdown content
			for (var md_idx in panel.markdowns) {
				var md_element = $('<div class="ui-md-el">')
					.attr('data-md-name', panel.markdowns[md_idx].name)
					.html(this.markdownToHtml(panel.markdowns[md_idx].desc));
				panel_content_el.append(md_element);
			}

			var form_el = $('<ol class="form">');

			for (var f_idx in panel.settings) {
				var settings = { ...panel.settings[f_idx] };

				settings.wrapperEl = 'li';
				settings.fieldClass = 'set_ui_option';
				settings.id = 'genericOption_' + settings.name;
				settings.data = {
					field: settings.name,
					section: settings.section
				}

				form_el.append(this.buildField(settings));
			}

			for (var f_idx in panel.fn_binds) {
				var settings = { ...panel.fn_binds[f_idx] };

				settings.wrapperEl = 'li';
				settings.fieldClass = 'set_ui_binding_value';
				settings.id = 'genericBinding_' + settings.name;
				settings.data = {
					field: settings.name,
				}

				form_el.append(this.buildField(settings));
			}

			panel_content_el.append(form_el);
			panel_content_el.append(this.buildQuickbuttons(panel.quickbuttons));

			panel_el.append(panel_content_el);

			$('#custom-ui').append(panel_el);
		}

		// load panel state
		for (var panel_id in rotorhazard.panelstates) {
			var panel_obj = $('#' + panel_id);
			var panelstate = rotorhazard.panelstates[panel_id];

			if (panelstate) {
				panel_obj.addClass('open');
				panel_obj.children('.panel-content').stop().slideDown();
			} else {
				panel_obj.removeClass('open');
				panel_obj.children('.panel-content').stop().slideUp();
			}
		}
	},
	_panelUpdatesPage: null,
	listenPanelUpdates: function(page) {
		// applies single field and markdown changes to this page's plugin panels
		if (this._panelUpdatesPage !== null) {
			return;
		}
		this._panelUpdatesPage = page;
		var rhuiObj = this;
		socket.on('ui_field_update', function (msg) {
			if (msg.page == page) {
				rhuiObj.applyFieldUpdate(msg);
			}
		});
		socket.on('ui_markdown_update', function (msg) {
			if (msg.page == page) {
				rhuiObj.applyMarkdownUpdate(msg);
			}
		});
	},
	applyFieldUpdate: function(msg) {
		var panel_el = $('#ui-custom-' + msg.panel);
		var field = panel_el.find('[id="genericOption_' + msg.name + '"], [id="genericBinding_' + msg.name + '"]').first();
		if (!field.length) {
			return;
		}
		if (msg.options) {
			var current = field.val();
			field.empty();
			for (var opt_id in msg.options) {
				$('<option>')
					.attr('value', msg.options[opt_id].value)
					.text(msg.options[opt_id].label)
					.appendTo(field);
			}
			if (field.find('option').filter(function () { return this.value == current; }).length) {
				field.val(current);
			}
		}
		if ('value' in msg) {
			if (field.is('output')) {
				field.text(msg.value == null ? '' : msg.value);
			} else if (field.attr('type') == 'checkbox') {
				field.prop('checked', Boolean(msg.value));
			} else if (!field.is(':focus')) {  // leave a value the user is typing
				field.val(msg.value);
				if (field.attr('type') == 'range') {
					this.updateRangeValue(field);
				}
			}
		}
	},
	applyMarkdownUpdate: function(msg) {
		var panel_content_el = $('#ui-custom-' + msg.panel).children('.panel-content');
		if (!panel_content_el.length) {
			return;
		}
		var md_element = panel_content_el.children('.ui-md-el').filter(function () {
			return $(this).attr('data-md-name') == msg.name;
		});
		if (!md_element.length) {
			md_element = $('<div class="ui-md-el">').attr('data-md-name', msg.name);
			var last_md = panel_content_el.children('.ui-md-el').last();
			if (last_md.length) {
				last_md.after(md_element);
			} else {
				panel_content_el.prepend(md_element);
			}
		}
		md_element.html(this.markdownToHtml(msg.desc));
	},
	buildQuickbuttons: function(btn_list) {
		var btn_list_el = $('<div class="control-set">');
		for (var idx in btn_list) {
			btn_el = $('<button>')
				.addClass('quickbutton')
				.text(btn_list[idx].label)
				.data('btn_id', btn_list[idx].name)

			btn_list_el.append(btn_el)
		}
		return btn_list_el
	}
}

$(document).ready(function () {
	$('.uifield-range input[type="range"]').each(function () {
		rhui._bindRangeValue($(this));
		rhui.updateRangeValue($(this));
	});

	$(document).on('click', '.quickbutton', function (event) {
		var data = {
			id: $(this).data('btn_id'),
			namespace: 'quickbutton'
		};
		socket.emit('dispatch_event', data);
	});

	$(document).on('change', '.set_ui_option', function (event) {
		var field = $(this).data('field');
		var section = $(this).data('section');
		var value = rhui.getFieldVal(this);

		if (section) {
			var data = {
				section: section,
				key: field,
				value: value
			};
			socket.emit('set_config', data);
		} else {
			var data = {
				option: field,
				value: value
			};
			socket.emit('set_option', data);
		}
	});

	$(document).on('change', '.set_ui_binding_value', function (event) {
		var data = {
			name: $(this).data('field'),
			value: rhui.getFieldVal(this)
		};
		socket.emit('set_ui_binding_value', data);
	});
});
