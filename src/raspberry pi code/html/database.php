<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>Database - Delta5 VTX Timer</title>

	<!-- Page styles -->
	<link rel="stylesheet" href="styles/mdl/material.min.css">
	<script src="styles/mdl/material.min.js"></script>
	<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
	
	<link rel="stylesheet" href="styles/styles.css"> <!-- superseding delta5 style sheet -->
	<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
	
	<!--Form posting functions	-->
	<?php
	if (isset($_POST['initializeSystem'])) {
		$numberOfNodes = htmlentities($_POST['numberOfNodes']);
		exec("sudo python /home/pi/VTX/initializeSystem.py ".$numberOfNodes);
	}

	if (isset($_POST['clearSavedRaces'])) {
		exec("sudo python /home/pi/VTX/clearSavedRaces.py");
		exec("sudo python /home/pi/VTX/clearLaps.py"); // Also clear current laps
	}

	if (isset($_POST['resetGroups'])) {
		exec("sudo python /home/pi/VTX/resetGroups.py");
		exec("sudo python /home/pi/VTX/setGroup.py 1"); // Then set group 1 to reset nodes
	}

	if (isset($_POST['resetPilots'])) {
		exec("sudo python /home/pi/VTX/resetPilots.py");
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
		<a class="delta5-navigation mdl-navigation__link" href="settings.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Settings</button></a>
	</nav>
	<div class="mdl-layout-spacer"></div>
	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="database.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Database</button></a>
	</nav>
	<span class="mdl-layout-title">
		<img src="images/delta5fpv.jpg">
	</span>
</div>
</header>

<!--Main content-->
<main class="mdl-layout__content">
<div class="page-content">

<!--Clear saved laps, reset groups, reset pilots-->
<div class="delta5-margin">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="clearSavedRaces">Clear Races</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="resetGroups">Reset Groups</button>&nbsp;
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="resetPilots">Reset Pilots</button>
</form>
</div>

<!--Get the number of nodes in the system and initialize the database-->
<h6>Initialize System (Warning, destroys all data)</h6>
<div class="delta5-margin">
<form method="post">
	<select name="numberOfNodes">
		<?php for ($i = 1; $i <= 6; $i++): ?>
		<option value="<?php echo $i ?>">
			<?php echo $i ?>
		</option>
		<?php endfor; ?>
	</select>
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="initializeSystem">Initialize System</button>
</form>
</div>

</div>
</main>

</div>
</body>

</html>
