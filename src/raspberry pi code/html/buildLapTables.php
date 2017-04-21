<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$nodes = $conn->query("SELECT node FROM nodes WHERE 1");

while ($node = $nodes->fetch_assoc()) :
?>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Pilot:</th>
		<th><?php echo $node['node']; ?></th>
	</tr>
</thead>
<tbody>

<?php $laps = $conn->query("SELECT * FROM currentLaps WHERE pilot = ".$node['node']);?>

<?php while ($row = $laps->fetch_assoc()) : ?>
<tr>
	<td><?php echo $row['lap']; ?></td>
	<td><?php echo $row['min']; ?>:<?php echo $row['sec']; ?>:<?php echo $row['milliSec']; ?></td>
</tr>
<?php endwhile ?>

</tbody>
</table>
</div>

<?php endwhile ?>
