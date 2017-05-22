<!doctype html>

<html lang="en">

<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>Race - Delta5 VTX Timer</title>

	<!-- Page styles -->
	<link rel="stylesheet" href="styles/mdl/material.min.css">
	<script src="styles/mdl/material.min.js"></script>
	<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
	
	<link rel="stylesheet" href="styles/styles.css"> <!-- superseding delta5 style sheet -->
	<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
	
	<!--Form posting functions	-->
	<?php
	if (isset($_POST['startRace'])) 
		{exec("sudo python /home/pi/VTX/startRace.py");
	}
	if (isset($_POST['stopRace'])) {
		exec("sudo python /home/pi/VTX/stopRace.py");
	}
	if (isset($_POST['saveLaps'])) {
		exec("sudo python /home/pi/VTX/saveLaps.py");
		exec("sudo python /home/pi/VTX/clearLaps.py"); // after saving the laps then clear currentLaps
	}
	if (isset($_POST['clearLaps']))	{
		exec("sudo python /home/pi/VTX/clearLaps.py");
	}
	?>
</head>
	
<body>
<div class="mdl-layout mdl-js-layout mdl-layout--fixed-header">

<!--Navigation-->
<header class="delta5-header mdl-layout__header">
<div class="delta5-navigation mdl-layout__header-row">
	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="index.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Races</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="groups.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Groups</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="race.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Race</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="system.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">System</button></a>
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

<!--Main content-->
<main class="mdl-layout__content">
<div class="page-content">

<!--Initial database connection for following sections-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Button for controlling the race-->
<div class="delta5-margin">
<form method="post">
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="startRace">Start Race</button>&nbsp;
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="stopRace">Stop Race</button>&nbsp;
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="saveLaps">Save Laps</button>&nbsp;
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="clearLaps">Clear Laps</button>
</form>
</div>

<!--Display the status of the race variable in a heading-->
<div>
<?php $results = $conn->query("SELECT `raceStatus` FROM `status`") or die($conn->error());
$status = $results->fetch_assoc(); ?>
<h5>Race Status: 
<?php if ($status['raceStatus'] == 0) { echo "Stopped"; }
else { echo "Racing!"; } ?>
</h5>
</div>

<!--Display the race leaderboard-->
<h5>Leaderboard</h5>
<div id="leaderboard">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#leaderboard').load('buildLeaderboard.php') }, 2000); } );
	</script>
</div>

<!--Display the current races laps-->
<h5>Laps</h5>
<div id="currentLaps">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#currentLaps').load('buildLapsCurrent.php') }, 1000); } );
	</script>
</div>


</div>
</main>

</div>
</body>

</html>
