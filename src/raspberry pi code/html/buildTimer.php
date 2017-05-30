<style class="cp-pen-styles">
div.timer {
	padding: 20px 0;    
	border:1px #666666 solid;
	width:270px;

	line-height:50px;
	font-size:100px;
	font-family:"arial", Courier, monospace;
	text-align:center;
	margin:5px;
}
</style>

<audio id="buzzer" src="sounds/beep.mp3" type="audio/mp3"></audio>    
<audio id="countdown" src="sounds/countdown10.mp3" type="audio/mp3"></audio>    
<audio id="thirtysec" src="sounds/30seconds.mp3" type="audio/mp3"></audio>    
<audio id="onemin" src="sounds/1minute.mp3" type="audio/mp3"></audio>    

<script>
function _timer(callback) {
	var time = 0; // The default time of the timer
	var mode = 1; // Mode: count up or count down
	var status = 0; // Status: timer is running or stoped
	var timer_id; // This is used by setInterval function

	var buzzer = $('buzzer')[0];
	var countdown = $('countdown')[0];
	var thirtysec = $('thirtysec')[0];
	var onemin = $('onemin')[0];
	
	// Start the timer with 1 second interval, timer.start(1000) 
	this.start = function(interval) {
		interval = (typeof(interval) !== 'undefined') ? interval : 1000;
 
		if(status == 0) { // If status stopped
			status = 1; // Set status to running
			timer_id = setInterval(function() {
				switch(mode) {
				default: // Default mode 0 for a countdown timer
					if(time) {
						time--;
						generateTime(); // Updates html timer text
						if(typeof(callback) === 'function') callback(time);
					}
					break;
				case 1: // Mode 1 for a count up timer
					if(time < 86400) {
						time++;
						generateTime(); // Updates html timer text
						if(typeof(callback) === 'function') callback(time);
					}
					break;
				}
			}, interval);
		}
	}
	
	// Same as the name, this will stop or pause the timer ex. timer.stop()
	this.stop =  function() {
		if(status == 1) {
			status = 0;
			clearInterval(timer_id);
		}
	}
	
	// Reset the timer to zero or reset it to your own custom time ex. reset to zero second timer.reset(0)
	this.reset =  function(sec) {
		this.stop(); // On a reset also stop the clock
		sec = (typeof(sec) !== 'undefined') ? sec : 0;
		time = sec;
		generateTime(time);
	}
	
	// Change the mode of the timer, count-up (1) or countdown (0)
	this.mode = function(tmode) {
		mode = tmode;
	}
	
	// This methode return the current value of the timer
	this.getTime = function() {
		return time;
	}
	
	// This methode return the current mode of the timer count-up (1) or countdown (0)
	this.getMode = function() {
		return mode;
	}
	
	// This methode return the status of the timer running (1) or stoped (1)
	this.getStatus = function() {
		return status;
	}
	
	// This methode will render the time variable to minute:second format
	function generateTime() {
		var milli = Math.floor(time) % 100;
		var second = Math.floor(time / 100) % 60;
		var minute = Math.floor(time / 6000) % 60;
		var hour = Math.floor(time / 3600) % 60;

		milli = (milli < 10) ? '0'+milli : milli;        
		second = (second < 10) ? '0'+second : second;
		minute = (minute < 10) ? '0'+minute : minute;

		// $('div.timer span.milli').html(milli);
		$('div.timer span.second').html(second);
		$('div.timer span.minute').html(minute);
	}
}

// Create the timer object
var timer;
timer = new _timer (
	function(time) {
		// At 0 seconds stop the timer and play the buzzer
		if(time == 0) { buzzer.play(); timer.stop(); }
		// At 10 seconds start the by second voice countdown
		if(time == 1100) { countdown.play(); }
		// At 30 second call out remaining time
		if(time == 3000) { thirtysec.play(); }
		// At 60 second call out remaining time
		if(time == 6000) { onemin.play(); }
		// Play the buzzer one milli second after the reset time
		if(time == 11999) { buzzer.play(); }
	}
);

timer.reset(120000/10); // Set initial time
timer.mode(0); // Set initial mode
</script>

<!--Show timer-->
<div class="timer delta5-float">
	<span class="minute">00</span>:<span class="second">00</span>
</div>
<div class="delta5-float">
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" onClick="timer.start(10)">Start</button>&nbsp;
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" onClick="timer.reset(120000/10)">Reset</button>
</div>
<div style="clear: both;"></div>
