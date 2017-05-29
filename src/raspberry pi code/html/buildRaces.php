<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the distinct number of groups to loop through-->
<?php $groupResults = $conn->query("SELECT DISTINCT `group` FROM `savedRaces`") or die($conn->error());
while ($group = $groupResults->fetch_assoc()): ?>

<h6>Group <?php echo $group['group']; ?></h6>

<!--Get the distinct race rows for each group-->
<?php $raceResults = $conn->query("SELECT DISTINCT `race` FROM `savedRaces` WHERE `group` = ".$group['group']) or die($conn->error());
while ($race = $raceResults->fetch_assoc()): ?>

<h6>Race <?php echo $race['race']; ?></h6>

<!--Get the node info to loop through-->
<?php $nodeResults = $conn->query("SELECT `node`, `pilot` FROM `groups` WHERE `group` = ".$group['group']) or die($conn->error());
while ($node = $nodeResults->fetch_assoc()): ?>

<!--Build races table-->
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
<!--Get the laps to loop through-->
<?php $lapResults = $conn->query("SELECT `lap`, `min`, `sec`, `milliSec` FROM `savedRaces` WHERE `group` = ".$group['group']." AND `race` = ".$race['race']." AND `pilot` = ".$node['pilot']) or die($conn->error());
while ($lap = $lapResults->fetch_assoc()): ?>
<tr>
	<td><?php echo sprintf('%02d',$lap['min']).':'.sprintf('%02d',$lap['sec']).'.'.sprintf('%03d',$lap['milliSec']); ?></td>
</tr>

<?php endwhile; ?>

</tbody>
</table>
</div>

<?php endwhile; ?> <!--Node end-->

<div style="clear: both;"></div>

<?php endwhile; ?> <!--Race end-->

<?php endwhile; ?> <!--Group end-->

<!--Add a group summary table of all the groups races showing pilot laps completed and lap stats similar to leaderboard table-->
