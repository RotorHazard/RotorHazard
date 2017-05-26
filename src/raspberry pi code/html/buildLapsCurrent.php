<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the current group-->
<?php $groupResults = $conn->query("SELECT `group` FROM `config`") or die($conn->error());
$group = $groupResults->fetch_assoc() ?>

<!--Get the node info to loop through-->
<?php $nodeResults = $conn->query("SELECT `node`, `pilot` FROM `groups` WHERE `group` = ".$group['group']) or die($conn->error());
while ($node = $nodeResults->fetch_assoc()): ?>

<!--Build laps table-->
<div class="delta5-margin delta5-float">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 120px;">
<thead>
<tr>
	<!--Display the current pilot and completed laps-->
	<?php $callSignResults = $conn->query("SELECT `callSign` FROM `pilots` WHERE `pilot` =".$node['pilot']) or die($conn->error());
	$callSign = $callSignResults->fetch_assoc(); ?>
	<th><?php echo $callSign['callSign']; ?></th>
</tr>
</thead>

<tbody>
<!--Get the number of laps to loop through-->
<?php $lapResults = $conn->query("SELECT `lap`, `min`, `sec`, `milliSec` FROM `currentLaps` WHERE `pilot` = ".$node['pilot']) or die($conn->error());
while ($lap = $lapResults->fetch_assoc()): ?>
<tr>
	<td><?php echo $lap['min'].':'.sprintf('%02d',$lap['sec']).':'.sprintf('%03d',$lap['milliSec']); ?></td>
</tr>
<?php endwhile; ?>

</tbody>
</table>
</div>

<?php endwhile; ?>

<div style="clear: both;"></div>
