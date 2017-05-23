<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the current group-->
<?php $results = $conn->query("SELECT `group` FROM `config`") or die($conn->error());
$group = $results->fetch_assoc() ?>

<!--Get the number of nodes to loop through-->
<?php $nodes = $conn->query("SELECT `node` FROM `nodes` WHERE 1") or die($conn->error());
while ($node = $nodes->fetch_assoc()) : ?>

<!--Build laps table-->
<div class="delta5-margin delta5-float">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 120px;">
<thead>
<tr>
	<!--Display the current pilot and completed laps-->
	<?php $results = $conn->query("SELECT `pilot` FROM `groups` WHERE `group` = ".$group['group']." AND `node` = ".$node['node']) or die($conn->error());
	$pilot = $results->fetch_assoc();
	$results = $conn->query("SELECT `callSign` FROM `pilots` WHERE `pilot` =".$pilot['pilot']) or die($conn->error());
	$pilotCallSign = $results->fetch_assoc(); ?>
	<th><?php echo $pilotCallSign['callSign']; ?></th>
</tr>
</thead>

<tbody>
<!--Get the number of laps to loop through-->
<?php $laps = $conn->query("SELECT * FROM `currentLaps` WHERE `pilot` = ".$node['node']) or die($conn->error());
while ($row = $laps->fetch_assoc()) : ?>
<tr>
	<td><?php echo $row['min'].':'.$row['sec'].':'.sprintf('%03d',$row['milliSec']); ?></td>
</tr>
<?php endwhile ?>

</tbody>
</table>
</div>

<?php endwhile ?>

<div style="clear: both;"></div>
