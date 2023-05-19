
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
	}
}