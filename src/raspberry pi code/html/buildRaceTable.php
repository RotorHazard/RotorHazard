<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$result = $conn->query("SELECT pilot, MAX(lap) FROM currentLaps GROUP BY pilot ORDER BY MAX(lap) DESC");
?>


<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Position</th>
		<th>Pilot</th>
		<th>Laps</th>
	</tr>
</thead>
<tbody>

<?php
$position = 0;
while ($row = $result->fetch_assoc()) :
$position ++;
?>
<tr>
	<td><?php echo $position ?></td>
	<td><?php echo $row['pilot']; ?></td>
	<td><?php echo $row['MAX(lap)']; ?></td>
</tr>
<?php endwhile ?>

</tbody>
</table>
</div>

