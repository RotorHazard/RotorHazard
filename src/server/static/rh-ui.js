
var rhui = {
	buildField: function(field_options) {
		var settings = {
			data: {},
			fieldClass: null,
			fieldType: null,
			genericOption: null,
			id: null,
			label: null,
			// TODO: labelNote: null,
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

		if (settings.fieldType == 'text') {
			var labelWrap = $('<div class="label-block"></div>');

			var label = $('<label>')
				.attr('for', settings.id)
				.text(settings.label);

			labelWrap.append(label);

			var field = $('<input>')
				.addClass(settings.fieldClass)
				.attr('id', settings.id)
				.attr('type', 'text')
				.val(settings.value);

			if (settings.genericOption) {
				field.addClass('set-option')
					.data('option', settings.genericOption)
			}

			for (var idx in settings.data) {
				field.data(idx, settings.data[idx])
			}

			wrapper.append(labelWrap);
			wrapper.append(field);
		} else {
			console.log('fieldtype not supported');
			return false;
		}

		return wrapper
	}
}