
var rhui = {
	buildField: function(field_options) {
		var settings = {
			data: {},
			desc: null,
			fieldClass: null,
			fieldType: null,
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
			settings[item] = field_options[item];
		}

		if (settings.wrapperEl) {
			var wrapper = $('<' + settings.wrapperEl + '>');
		} else {
			var wrapper = $('<div>');
		}

		if (settings.wrapperClass) {
			wrapper.addClass(settings.wrapperClass);
		}

		var labelWrap = $('<div class="label-block"></div>');

		var label = $('<label>')
			.attr('for', settings.id)
			.text(settings.label);

		labelWrap.append(label);

		if (settings.desc) {
			labelWrap.append('<p class="desc">' + settings.desc + '</p>');
		}

		if (settings.fieldType == 'text') {
			var field = $('<input>')
				.attr('type', 'text')
				.attr('placeholder', settings.placeholder);

			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.fieldType == 'basic_int') {
			var field = $('<input>')
				.attr('type', 'number')
				.attr('min', 0)
				.attr('max', 999)
				.attr('step', 1)
				.attr('placeholder', settings.placeholder);

			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.fieldType == 'select') {
			var field = $('<select>')

			for (var opt_id in settings.options) {
				var opt = settings.options[opt_id];

				var opt_el = $('<option>')
					.attr('value', opt.name)
					.text(opt.value);
				field.append(opt_el);
			}
			settings.value = settings.options[0].name;

			wrapper.append(labelWrap);
			wrapper.append(field);
		} else if (settings.fieldType == 'checkbox') {
			var field = $('<input>')
				.attr('type', 'checkbox')
				.prop('checked', settings.value);

			wrapper.append(labelWrap);
			wrapper.append(field);
		} else {
			console.log('fieldtype not supported');
			return false;
		}

		field.addClass(settings.fieldClass)
			.attr('id', settings.id)
			.val(settings.value);

		if (settings.genericOption) {
			field.addClass('set-option')
				.data('option', settings.genericOption)
		}

		for (var idx in settings.data) {
			field.data(idx, settings.data[idx])
		}

		return wrapper
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
	$(document).on('click', '.quickbutton', function (event) {
		var data = {
			id: $(this).data('btn_id'),
			namespace: 'quickbutton'
		};
		socket.emit('dispatch_event', data);
	});
});
