function createBandScanner(elementId) {
	let channels = [
		{freq:5658, name:'R1'},
		{freq:5695, name:'R2'},
		{freq:5760, name:'F2'},
		{freq:5800, name:'F4'},
		{freq:5880, name:'R7'},
		{freq:5917, name:'R8'}
	];
	let canvas = document.getElementById(elementId);
	let chart = new Chart(canvas, {
		type: 'bar',
		data: {
			labels: [],
			datasets: [{
				type: 'line',
				label: '',
				pointRadius: 0,
				borderColor: '#ff0000',
				borderWidth: 1,
				fill: false,
				data: []
			}, {
				type: 'line',
				label: '',
				pointRadius: 0,
				borderColor: '#222222',
				borderWidth: 1,
				fill: false,
				data: []
			}, {
				label: '',
				backgroundColor: '#0000ff',
				data: []
			}]
		},
		options: {
			scales: {
				xAxes: [{
					barPercentage: 1,
					categoryPercentage: 1,
					ticks: {
						fontSize: 10,
						lineHeight: 2,
						callback: function(dataLabel, index) {
							let freq = parseInt(dataLabel);
							for(let chan of channels) {
								let chanFreq = chan.freq;
								if(freq >= chanFreq-5 && freq <= chanFreq+5) {
									return [dataLabel, chan.name];
								}
							}
							return dataLabel;
						}
					}
				}],
				yAxes: [{
					type: 'linear',
					ticks: {
						min: 0,
						max: 100
					}
				}]
			},
			legend: {
				display: false
			},
			tooltips: {
				enabled: false
			}
		}
	});
	let scanner = {
		chart: chart.chart,
		update: function(freq, rssiValue) {
			if (freq > 0) {
				this.chart.options.scales.yAxes[0].ticks.max = Math.max(
					rssiValue + 10,
					this.chart.options.scales.yAxes[0].ticks.max
				);

				let idx;
				let labels = this.chart.data.labels;
				for (idx = 0; idx < labels.length; idx++) {
					if (freq === labels[idx]) {
						break;
					} else if (freq < labels[idx]) {
						idx = -idx - 1;
						break;
					}
				}

				let max_data = this.chart.data.datasets[0].data;
				let min_data = this.chart.data.datasets[1].data;
				let current_data = this.chart.data.datasets[2].data;
				if(idx >= 0 && idx < labels.length) {
					current_data[idx] = rssiValue;
					min_data[idx] = (rssiValue > 0 && rssiValue < min_data[idx]) ? rssiValue : min_data[idx];
					max_data[idx] = Math.max(rssiValue, max_data[idx]);
				} else if (idx >= labels.length) {
					labels.push(freq);
					current_data.push(rssiValue);
					min_data.push(rssiValue);
					max_data.push(rssiValue);
				} else {
					idx = -idx - 1;
					labels.splice(idx, 0, freq);
					current_data.splice(idx, 0, rssiValue);
					min_data.splice(idx, 0, rssiValue);
					max_data.splice(idx, 0, rssiValue);
				}
				this.chart.update();
			}
		},
		clear: function() {
			for (let i = 0; i < this.chart.data.datasets.length; i++) {
				this.chart.data.datasets[i].data = [];
			}
			this.chart.update();
		}
	}
	return scanner;
}

function registerMessageHandlers(socket, scanners) {
	socket.on('heartbeat', function (msg) {
		for (let i = 0; i < msg.current_rssi.length; i++) {
			let scanner = scanners[i];
			if (scanner && scanner.isEnabled) {
				let rssiValue = msg.current_rssi[i];
				let freq = msg.frequency[i];
				scanner.update(freq, rssiValue);
			}
		}
	});
}
