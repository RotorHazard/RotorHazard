<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Build pilots table-->
<div class="delta5-margin">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Pilot</th>
		<th>Callsign</th>
		<th>Name</th>
	</tr>
</thead>
<tbody>

<!--Get pilots info to loop through-->
<?php $pilots = $conn->query("SELECT * FROM `pilots` WHERE 1") or die($conn->error());
while ($pilot = $pilots->fetch_assoc()):
if ($pilot['pilot'] != 0):?>
<tr>
	<td><?php echo $pilot['pilot']; ?></td>
	<td>
	<form method="post">
		<!--Display the current pilot call sign-->
		<?php $results = $conn->query("SELECT `callSign` FROM `pilots` WHERE `pilot` = ".$pilot['pilot']) or die($conn->error());
		$callSign = $results->fetch_assoc(); ?>
		<input name="setCallSign" onchange="this.form.submit()" value="<?php echo $callSign['callSign']; ?>" style="width:120px">
		<!--Pilot ID to know which pilot to update-->
		<input name="pilotid" value="<?php echo $pilot['pilot']; ?>" type="hidden"/>
	</form>	
	</td>
	<td>
	<form method="post">
		<!--Display the pilot name-->
		<?php $results = $conn->query("SELECT `name` FROM `pilots` WHERE `pilot` = ".$pilot['pilot']) or die($conn->error());
		$name = $results->fetch_assoc(); ?>
		<input name="setPilotName" onchange="this.form.submit()" value="<?php echo $name['name']; ?>" style="width:120px">
		<!--Pilot ID to know which pilot to update-->
		<input name="pilotid" value="<?php echo $pilot['pilot']; ?>" type="hidden"/>
	</form>		
	</td>
</tr>
<?php
endif;
endwhile;
?>

</tbody>
</table>
</div>
