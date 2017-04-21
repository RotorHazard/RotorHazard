<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$setups = $conn->query("SELECT * FROM setup");

while ($setup = $setups->fetch_assoc()) :
?>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Setup</th>
		<th>Data</th>
	</tr>
</thead>
<tbody>
<tr>
	<td>Node Comms:</td>
	<td><?php echo $setup['commsStatus']; ?></td>
</tr>
<tr>
	<td>Racing:</td>
	<td><?php echo $setup['raceStatus']; ?></td>
</tr>
<tr>
	<td>Min Lap Time:</td>
	<td><?php echo $setup['minLapTime']; ?></td>
</tr>
</tbody>
</table>
</div>

<?php endwhile ?>