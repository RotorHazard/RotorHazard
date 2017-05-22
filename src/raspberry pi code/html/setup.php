<!doctype html>

<html lang="en">

<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>Setup - Delta5 VTX Timer</title>

	<!-- Page styles -->
	<link rel="stylesheet" href="styles/mdl/material.min.css">
	<script src="styles/mdl/material.min.js"></script>
	<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
	
	<link rel="stylesheet" href="styles/styles.css"> <!-- superseding delta5 style sheet -->
	<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
	
	<!--Form posting functions	-->
	<?php
	if (isset($_GET['initializeSystem'])) {
		$numberOfNodes = htmlentities($_GET['numberOfNodes']);
		exec("sudo python /home/pi/VTX/initializeSystem.py ".$numberOfNodes);
	}
	if (isset($_POST['createDatabase'])) {
		exec("sudo python /home/pi/VTX/createDatabase.py");
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
		<a class="delta5-navigation mdl-navigation__link" href="race.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Race</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="system.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">System</button></a>
	</nav>
	<div class="mdl-layout-spacer"></div>
	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="setup.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Setup</button></a>
	</nav>
	<span class="mdl-layout-title">
		<img src="images/delta5fpv.jpg">
	</span>
</div>
</header>

<!--Main content-->
<main class="mdl-layout__content">
<div class="page-content">

<!--Get the number of nodes in the system and initialize the database-->
<h5>Initialize System</h5>
<div class="delta5-margin">
<form method="get">
<div class="mdl-textfield mdl-js-textfield" style="width:150px;">
	<input name="numberOfNodes" id="numberOfNodes" class="mdl-textfield__input" type="text" pattern="-?[0-9]*(\.[0-9]+)?">
	<label for="numberOfNodes" class="mdl-textfield__label">Number of nodes...</label>
	<span class="mdl-textfield__error">Input is not a number!</span>
</div>
<br>
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="initializeSystem">Initialize System</button>
</form>
</div>

<!--Empty and create the database new-->
<h5>Create Database (Warning, destroys all data)</h5>
<div class="delta5-margin">
<form method="post">
<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="createDatabase">Create Database</button>
</form>
</div>

</div>
</main>

</div>
</body>

</html>