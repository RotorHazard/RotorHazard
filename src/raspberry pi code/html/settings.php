<!doctype html>

<html lang="en">

<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>Settings - Delta5 VTX Timer</title>

	<!-- Page styles -->
	<link rel="stylesheet" href="mdl/material.min.css">
	<script src="mdl/material.min.js"></script>
	<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
	
	<link rel="stylesheet" href="styles.css">
	<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
		
	<?php
	# Start / Stop system commands
	if (isset($_POST['startSystem'])) {exec("sudo python /home/pi/VTX/startSystem.py"); }
	if (isset($_POST['stopSystem'])) {
		exec("sudo python /home/pi/VTX/stopRace.py"); # Also 'stopRace' if stopping comms
		exec("sudo python /home/pi/VTX/stopSystem.py");
	}
	
	# Set min lap time
	if (isset($_POST['setMinLapTime'])) {
		$minLapTime = htmlentities($_POST['minLapTime']);
		exec("sudo python /home/pi/VTX/setMinLapTime.py ".$minLapTime);
	}

	# Set vtx channel / frequency
	if (isset($_POST['setVtxFrequency'])) {
		$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
		if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }
		$result = $conn->query("SELECT `i2cAddr` FROM `nodes` WHERE `node` = ".$_POST['nodeid']) or die($conn->error());

		while($node = $result->fetch_assoc()) {	
			$vtxFrequency = htmlentities($_POST['vtxFrequency']);
			exec("sudo python /home/pi/VTX/setVtxFrequency.py ".$node['i2cAddr']." ".$vtxFrequency);
		}
		$conn->close();
	}
	
	# Set rssi trigger value
	if (isset($_POST['rssiTrigger']) && isset($_POST['nodeid'])) {
		$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
		if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }
		$results = $conn->query("SELECT `rssi` FROM `nodesMem` WHERE `node` = ".$_POST['nodeid']) or die($conn->error());
		$rssi = $results->fetch_assoc();
		$results = $conn->query("SELECT `i2cAddr`, `rssiTrigger` FROM `nodes` WHERE `node` = ".$_POST['nodeid']) or die($conn->error());
		$node = $results->fetch_assoc();

		if ($_POST['rssiTrigger'] == 'Set') { $newrssi = $rssi['rssi']; }
		if ($_POST['rssiTrigger'] == 'Zero') { $newrssi = 0; }
		if ($_POST['rssiTrigger'] == 'Inc') { $newrssi = $node['rssiTrigger'] + 5; }
		if ($_POST['rssiTrigger'] == 'Dec') { $newrssi = $node['rssiTrigger'] - 5; }
		exec("sudo python /home/pi/VTX/setRssiTrigger.py ".$node['i2cAddr']." ".$newrssi);

		$conn->close();
	}
	?>
</head>
	
<body>
<div class="mdl-layout mdl-js-layout mdl-layout--fixed-header">

<header class="delta5-header mdl-layout__header">
<div class="delta5-navigation mdl-layout__header-row">

	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="index.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Races</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="pilots.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Pilots</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="groups.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Groups</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="manage.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Manage</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="settings.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Settings</button></a>
	</nav>
	
	<div class="mdl-layout-spacer"></div>
	
	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="setup.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Setup</button></a>
	</nav>
	
	<span class="mdl-layout-title">
		<img src="images/delta5fpv.jpg">
	</span>
	
</div>
</header>

<main class="mdl-layout__content">
<div class="page-content">

<div class="mdl-grid"><div class="mdl-cell mdl-cell--12-col">
<form method="post">
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="startSystem">Start System</button>&nbsp;
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="stopSystem">Stop System</button>
</form>
</div></div>


<div><h5>System Status</h5></div>
<div class="mdl-grid">
<div class="mdl-cell mdl-cell--2-col" id="setupData">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#setupData').load('buildSystemStatusTable.php') }, 1000); } );
	</script>
</div>
<div class="mdl-cell mdl-cell--2-col">
<form method="post">
	<div class="mdl-textfield mdl-js-textfield">
		<input class="mdl-textfield__input" type="text" pattern="-?[0-9]*(\.[0-9]+)?" id="minLapTime" name="minLapTime">
		<label class="mdl-textfield__label" for="minLapTime">Set minLapTime...</label>
		<span class="mdl-textfield__error">Input is not a number!</span>
	</div>
	<br>
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="setMinLapTime">Set</button>
</form>
</div>
</div>


<div><h5>Nodes</h5></div>
<div class="mdl-grid" id="nodeData">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#nodeData').load('buildNodeTables.php') }, 1000); } );
	</script>
</div>
<div class="mdl-grid" id="nodeSetup">
	<script type="text/javascript">
	$(document).ready(function() { $('#nodeSetup').load('buildNodeSetup.php') } );
	</script>
</div>


<div><h5>Pilots</h5></div>
<div class="mdl-grid"><div class="mdl-cell mdl-cell--12-col">

<!-- Add content here -->

</div></div>


<div><h5>Groups</h5></div>
<div class="mdl-grid"><div class="mdl-cell mdl-cell--12-col">

<!-- Add content here -->

</div></div>


<footer class="delta5-footer mdl-mini-footer">
</footer>

</div>
</main>

</div>
</body>

</html>

