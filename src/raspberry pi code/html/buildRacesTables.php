<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$rounds = $conn->query("SELECT DISTINCT `round` FROM `savedRaces`") or die($conn->error());

while ($round = $rounds->fetch_assoc()) :

$groups = $conn->query("SELECT DISTINCT `group` FROM `savedRaces` WHERE `round` = ".$round['round']) or die($conn->error());

while ($group = $groups->fetch_assoc()) :
?>

<div><h6>Round <?php echo $round['round']; ?>, Group <?php echo $group['group']; ?></h6></div>

<div class="mdl-grid">

<?php 
$nodes = $conn->query("SELECT `node` FROM `nodes` WHERE 1") or die($conn->error());

while ($node = $nodes->fetch_assoc()) :
?>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Pilot</th>
		<th><?php echo $node['node']; ?></th>
	</tr>
</thead>
<tbody>

<?php $laps = $conn->query("SELECT `lap`, `min`, `sec`, `milliSec` FROM `savedRaces` WHERE `round` = ".$round['round']." AND `group` = ".$group['group']." AND `pilot` = ".$node['node']) or die($conn->error());?>

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

</div>

<?php endwhile ?>

<?php endwhile ?>
