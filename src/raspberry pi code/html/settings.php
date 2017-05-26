<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>Settings - Delta5 VTX Timer</title>

	<!-- Page styles -->
	<link rel="stylesheet" href="styles/mdl/material.min.css">
	<script src="styles/mdl/material.min.js"></script>
	<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
	
	<link rel="stylesheet" href="styles/styles.css"> <!-- superseding delta5 style sheet -->
	<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>

	<!--Form posting functions	-->
	<?php
	// Start / Stop system commands
	if (isset($_POST['startSystem'])) {
		exec("sudo python /home/pi/VTX/startSystem.py");
	}
	if (isset($_POST['stopSystem'])) {
		exec("sudo python /home/pi/VTX/stopSystem.py");
		exec("sudo python /home/pi/VTX/stopRace.py"); // Also stop race
	}

	// Set group
	if (isset($_POST['setGroup'])) {
		$newGroup = htmlentities($_POST['setGroup']);
		exec("sudo python /home/pi/VTX/stopSystem.py");
		exec("sudo python /home/pi/VTX/setGroup.py ".$newGroup);
		exec("sudo python /home/pi/VTX/startSystem.py"); // Clean start up main system loop
	}

	// Set min lap time
	if (isset($_POST['setMinLapTime'])) {
		$minLapTime = htmlentities($_POST['setMinLapTime']);
		exec("sudo python /home/pi/VTX/stopSystem.py");
		exec("sudo python /home/pi/VTX/setMinLapTime.py ".$minLapTime);
		exec("sudo python /home/pi/VTX/startSystem.py"); // Clean start up main system loop
	}

	// Set pilot position in groups and nodes
	if (isset($_POST['setPilot'])) {
		$pilot = htmlentities($_POST['setPilot']);
		$group = htmlentities($_POST['groupid']);
		$node = htmlentities($_POST['nodeid']);
		exec("sudo python /home/pi/VTX/setPilotPosition.py ".$group." ".$node." '".$pilot."'");
	}

	// Set vtx channel / frequency
	if (isset($_POST['setVtxChannel'])) {
		$vtxChannel = htmlentities($_POST['setVtxChannel']);
		$group = htmlentities($_POST['groupid']);
		$node = htmlentities($_POST['nodeid']);
		exec("sudo python /home/pi/VTX/setVtxChannel.py ".$group." ".$node." '".$vtxChannel."'");
	}
	
	// Set rssi trigger value
	if (isset($_POST['setRssiTrigger'])) {
		$rssiTrigger = htmlentities($_POST['setRssiTrigger']);
		$group = htmlentities($_POST['groupid']);
		$node = htmlentities($_POST['nodeid']);
		exec("sudo python /home/pi/VTX/setRssiTrigger.py ".$group." ".$node." ".$rssiTrigger);
	}

	// Set pilot call sign
	if (isset($_POST['setCallSign'])) {
		$setCallSign = htmlentities($_POST['setCallSign']);
		$pilot = htmlentities($_POST['pilotid']);
		exec("sudo python /home/pi/VTX/setPilotCallSign.py ".$pilot." '".$setCallSign."'");
	}

	// Set set pilot name
	if (isset($_POST['setPilotName'])) {
		$setPilotName = htmlentities($_POST['setPilotName']);
		$pilot = htmlentities($_POST['pilotid']);
		exec("sudo python /home/pi/VTX/setPilotName.py ".$pilot." '".$setPilotName."'");
	}

	// Add new pilot
	if (isset($_POST['addPilot'])) {
		exec("sudo python /home/pi/VTX/addPilot.py");
	}

	// Add new group
	if (isset($_POST['addGroup'])) {
		exec("sudo python /home/pi/VTX/addGroup.py");
	}
	?>
</head>
	
<body>
<div class="mdl-layout mdl-js-layout mdl-layout--fixed-header">

<!--Navigation-->
<header class="delta5-header mdl-layout__header">
<div class="delta5-navigation mdl-layout__header-row">
	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="index.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Laps</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="groups.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Groups</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="race.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Race</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="settings.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Settings</button></a>
	</nav>
	<div class="mdl-layout-spacer"></div>
	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="database.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Database</button></a>
	</nav>
	<span class="mdl-layout-title">
		<img src="images/delta5fpv.jpg">
	</span>
</div>
</header>

<!--Main content-->
<main class="mdl-layout__content">
<div class="page-content">

<!--Initial database connection for following sections-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--System start stop buttons-->
<div class="delta5-margin">
<form method="post">
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="startSystem">Start System</button>&nbsp;
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="stopSystem">Stop System</button>
</form>
</div>

<!--System status table-->
<div id="systemStatus" class="delta5-float">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#systemStatus').load('buildSystemStatus.php') }, 1000); } );
	</script>
</div>
<!--Race status table-->
<div id="raceStatus" class="delta5-float">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#raceStatus').load('buildRaceStatus.php') }, 1000); } );
	</script>
</div>
<!--Config min lap time-->
<div id="configMinLap" class="delta5-float">
	<script type="text/javascript">
	$(document).ready(function() { $('#configMinLap').load('buildConfigMinLap.php') } );
	</script>
</div>
<!--Config current group-->
<div id="configGroup" class="delta5-float">
	<script type="text/javascript">
	$(document).ready(function() { $('#configGroup').load('buildConfigGroup.php') } );
	</script>
</div>
<div style="clear: both;"></div>

<!--Current group-->
<h6>Current Group</h6>

<!--Display the node data-->
<div id="nodeData">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#nodeData').load('buildNodes.php') }, 1000); } );
	</script>
</div>

<!--Display the current group data-->
<div id="currentGroup">
	<script type="text/javascript">
	$(document).ready(function() { $('#currentGroup').load('buildGroupCurrent.php') } );
	</script>
</div>

<!--Show all of the groups with editable tables-->
<div id="groups">
	<script type="text/javascript">
	$(document).ready(function() { $('#groups').load('buildGroupsEdit.php') } );
	</script>
</div>

<!--Add group button-->
<div class="delta5-margin">
<form method="post">
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="addGroup">Add Group</button>
</form>
</div>

<!--Show all of the pilots with editable tables-->
<h6>Pilots</h6>
<div id="pilots">
	<script type="text/javascript">
	$(document).ready(function() { $('#pilots').load('buildPilotsEdit.php') } );
	</script>
</div>

<!--Add pilot button-->
<div class="delta5-margin">
<form method="post">
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="addPilot">Add Pilot</button>
</form>
</div>

</div>
</main>

</div>
</body>

</html>
