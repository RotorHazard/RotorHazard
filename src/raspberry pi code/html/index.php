<!doctype html>

<html lang="en">

<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>Races - Delta5 VTX Timer</title>

	<!-- Page styles -->
	<link rel="stylesheet" href="mdl/material.min.css">
	<script src="mdl/material.min.js"></script>
	<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
	
	<link rel="stylesheet" href="styles.css"> <!-- superseding delta5 style sheet -->
	<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
</head>
	
<body>
<div class="mdl-layout mdl-js-layout mdl-layout--fixed-header">

<header class="delta5-header mdl-layout__header">
<div class="delta5-navigation mdl-layout__header-row">

	<nav class="mdl-navigation">
		<a class="delta5-navigation mdl-navigation__link" href="index.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">Races</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="pilots.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Pilots</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="groups.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Groups</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="manage.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Manage</button></a>
		<a class="delta5-navigation mdl-navigation__link" href="settings.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--colored">Settings</button></a>
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


<div><h5>Races</h5></div>
<div id="savedRaces">
	<script type="text/javascript">
	$(document).ready(function() { $('#savedRaces').load('buildRacesTables.php') } );
	</script>
</div>


<footer class="delta5-footer mdl-mini-footer">
</footer>

</div>
</main>

</div>
</body>

</html>
