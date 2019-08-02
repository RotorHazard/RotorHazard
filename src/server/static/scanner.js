function createBandScanner(elementId) {
	let canvas = document.getElementById(elementId);
	let chart = new Chart(canvas, {
		type: 'line',
		data: {
			datasets: [{
				label: '',
				pointRadius: 0,
				borderColor: '#0000ff',
				borderWidth: 2,
				fill: false,
				data: []
			}, {
				label: '',
				pointRadius: 0,
				borderWidth: 2,
				fill: false,
				data: []
			}, {
				label: '',
				pointRadius: 0,
				borderColor: '#ff0000',
				borderWidth: 2,
				fill: false,
				data: []
			}]
		},
		options: {
			scales: {
				xAxes: [{
					type: 'linear',
					ticks: {
						suggestedMin: 5645,
						suggestedMax: 5945
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
		update: function(datasetIndex, freq, rssiValue, merger) {
			if (freq > 0) {
				this.chart.options.scales.yAxes[0].ticks.max = Math.max(
					rssiValue + 10,
					this.chart.options.scales.yAxes[0].ticks.max
				);

				let data = this.chart.data.datasets[datasetIndex].data;
				let idx;
				for (idx = 0; idx < data.length; idx++) {
					if (freq === data[idx].x) {
						break;
					} else if (freq < data[idx].x) {
						idx = -idx - 1;
						break;
					}
				}

				if(idx >= 0 && idx < data.length) {
					data[idx].y = merger(data[idx].y, rssiValue);
				} else if (idx >= data.length) {
					data.push({x: freq, y: rssiValue});
				} else {
					idx = -idx - 1;
					data.splice(idx, 0, {x: freq, y: rssiValue});
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
	var latestMerger = function(oldRssi, newRssi) {
		return newRssi;
	}
	var maxMerger = function(oldRssi, newRssi) {
		return Math.max(oldRssi, newRssi);
	}
	var minMerger = function(oldRssi, newRssi) {
		return (newRssi > 0 && newRssi < oldRssi) ? newRssi : oldRssi;
	}

	socket.on('heartbeat', function (msg) {
		for (let i = 0; i < msg.current_rssi.length; i++) {
			let scanner = scanners[i];
			if (scanner && scanner.isEnabled) {
				let rssiValue = msg.current_rssi[i];
				let freq = msg.frequency[i];
				scanner.update(0, freq, rssiValue, latestMerger);
				scanner.update(1, freq, rssiValue, minMerger);
				scanner.update(2, freq, rssiValue, maxMerger);
			}
		}
	});
}
