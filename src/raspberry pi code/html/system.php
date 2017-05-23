<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge">
	<meta name="description" content="Delta5 VTX Timer.">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
	<title>System - Delta5 VTX Timer</title>

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
		exec("sudo python /home/pi/VTX/stopRace.py"); # Also 'stopRace' if stopping comms
		exec("sudo python /home/pi/VTX/stopSystem.py");
	}

	// Set min lap time
	if (isset($_POST['setMinLapTime'])) {
		$minLapTime = htmlentities($_POST['minLapTime']);
		exec("sudo python /home/pi/VTX/setMinLapTime.py ".$minLapTime);
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
		<a class="delta5-navigation mdl-navigation__link" href="system.php"><button class="delta5-navigation mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent">System</button></a>
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
<h5>System Status</h5>
<div id="setupData">
	<script type="text/javascript">
	$(document).ready(function() { setInterval(function() { $('#setupData').load('buildSystemStatus.php') }, 1000); } );
	</script>
</div>
<!--Set minimum lap time-->
<div class="delta5-margin">
<form method="post">
	<div class="mdl-textfield mdl-js-textfield" style="width:150px;">
		<input class="mdl-textfield__input" type="text" pattern="-?[0-9]*(\.[0-9]+)?" id="minLapTime" name="minLapTime">
		<label class="mdl-textfield__label" for="minLapTime">Set minLapTime...</label>
		<span class="mdl-textfield__error">Input is not a number!</span>
	</div>
	<br>
	<button class="mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect" name="setMinLapTime">Set</button>
</form>
</div>

<!--Display the current loaded group in the heading-->
<?php $results = $conn->query("SELECT `group` FROM `config`") or die($conn->error());
$group = $results->fetch_assoc(); ?>
<h5>Current Group: <?php echo $group['group']; ?>
<!--Build the drop down selection to change the group-->
<form method="post">
	<select name="setGroup" onchange="this.form.submit()">
		<!--Get groups list-->
		<?php $results = $conn->query("SELECT DISTINCT `group` FROM `groups` ORDER BY `group` ASC") or die($conn->error());
		$groups = array();
		while ($row = $results->fetch_assoc()) {
			$groups[] = $row;
		} ?>
		<!--Display the current group first-->
		<option value="<?php echo $group['group']; ?>"><?php echo $group['group']; ?></option>
		<!--Build the list of groups-->
		<?php for ($i = 0; $i < count($groups); $i++) : ?>
		<option value="<?php echo $groups[$i]['group']; ?>">
			<?php echo $groups[$i]['group']; ?>
		</option>
		<?php endfor ?>
	</select>
</form>
</h5>

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
<h5>Groups</h5>
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
<h5>Pilots</h5>
<div id="pilots">
	<script type="text/javascript">
	$(document).ready(function() { $('#pilots').load('buildPilots.php') } );
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
