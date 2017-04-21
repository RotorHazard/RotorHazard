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
	if (isset($_POST['startComms'])) {exec("sudo python /home/pi/VTX/startComms.py"); }
	if (isset($_POST['stopComms'])) {exec("sudo python /home/pi/VTX/stopComms.py");	}
	
	if (isset($_POST['node1rssiTriggerSet'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 1 8 set"); }
	if (isset($_POST['node1rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 1 8 dec"); }
	if (isset($_POST['node1rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 1 8 inc"); }
	if (isset($_POST['node2rssiTriggerSet'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 2 10 set"); }
	if (isset($_POST['node2rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 2 10 dec"); }
	if (isset($_POST['node2rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 2 10 inc"); }
	if (isset($_POST['node3rssiTriggerSet'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 3 12 set"); }
	if (isset($_POST['node3rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 3 12 dec"); }
	if (isset($_POST['node3rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 3 12 inc"); }
	if (isset($_POST['node4rssiTriggerSet'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 4 14 set"); }
	if (isset($_POST['node4rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 4 14 dec"); }
	if (isset($_POST['node4rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 4 14 inc"); }
	if (isset($_POST['node5rssiTriggerSet'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 5 16 set"); }
	if (isset($_POST['node5rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 5 16 dec"); }
	if (isset($_POST['node5rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 5 16 inc"); }
	if (isset($_POST['node6rssiTriggerSet'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 6 18 set"); }
	if (isset($_POST['node6rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 6 18 dec"); }
	if (isset($_POST['node6rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 6 18 inc"); }
	?>
</head>
	
<body>
<div class="mdl-layout mdl-js-layout mdl-layout--fixed-header">

<header class="delta5-header mdl-layout__header">
<div class="mdl-layout__header-row">

	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="index.php"><button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Races</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="pilots.php"><button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Pilots</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="groups.php"><button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Groups</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="manage.php"><button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Manage</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="settings.php"><button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Settings</button></a>
	</nav>
	
	<span class="mdl-layout-title">
		<img class="delta5-logo-image" src="images/delta5fpv.jpg">
	</span>
	
</div>
</header>

<main class="mdl-layout__content">
<div class="page-content">

<div class="mdl-grid"><h5>Nodes Communication</h5><div class="mdl-cell mdl-cell--12-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="startComms">Start Comms</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="stopComms">Stop Comms</button>
</form>
</div></div>

<h5>Setup Data</h5>
<div class="mdl-grid" id="setupData">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#setupData').load('buildSetupTable.php') }, 1000); } );
	</script>
</div>


<div class="mdl-grid">

<div class="mdl-cell mdl-cell--2-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node1rssiTriggerSet">Node 1 Trigger</button><br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node1rssiTriggerDec">-5</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node1rssiTriggerInc">+5</button>
</form>
</div>
<div class="mdl-cell mdl-cell--2-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node2rssiTriggerSet">Node 2 Trigger</button><br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node2rssiTriggerDec">-5</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node2rssiTriggerInc">+5</button>
</form>
</div>
<div class="mdl-cell mdl-cell--2-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node3rssiTriggerSet">Node 3 Trigger</button><br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node3rssiTriggerDec">-5</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node3rssiTriggerInc">+5</button>
</form>
</div>
<div class="mdl-cell mdl-cell--2-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node4rssiTriggerSet">Node 4 Trigger</button><br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node4rssiTriggerDec">-5</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node4rssiTriggerInc">+5</button>
</form>
</div>
<div class="mdl-cell mdl-cell--2-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node5rssiTriggerSet">Node 5 Trigger</button><br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node5rssiTriggerDec">-5</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node5rssiTriggerInc">+5</button>
</form>
</div>
<div class="mdl-cell mdl-cell--2-col">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node6rssiTriggerSet">Node 6 Trigger</button><br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node6rssiTriggerDec">-5</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="node6rssiTriggerInc">+5</button>
</form>
</div>

</div>

<h5>Node Data</h5>
<div class="mdl-grid" id="nodeData">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#nodeData').load('buildNodeTables.php') }, 1000); } );
	</script>
</div>


<div class="mdl-grid"><h5>Setup Pilots</h5><div class="mdl-cell mdl-cell--12-col">

</div></div>


<div class="mdl-grid"><h5>Setup Groups</h5><div class="mdl-cell mdl-cell--12-col">

</div></div>


<footer class="delta5-footer mdl-mini-footer">
</footer>

</div>
</main>

</div>
</body>

</html>

