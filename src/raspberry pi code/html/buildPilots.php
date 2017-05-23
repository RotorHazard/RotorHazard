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
while ($pilot = $pilots->fetch_assoc()) : ?>

<tr>
	<td><?php echo $pilot['pilot']; ?></td>
	<td><?php echo $pilot['callSign']; ?></td>
	<td><?php echo $pilot['name']; ?></td>
</tr>
<?php endwhile ?>

</tbody>
</table>
</div>
