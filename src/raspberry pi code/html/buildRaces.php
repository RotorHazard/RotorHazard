<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the distinct number of groups to loop through-->
<?php $groups = $conn->query("SELECT DISTINCT `group` FROM `savedRaces`") or die($conn->error());
while ($group = $groups->fetch_assoc()) : ?>

<h6>Group <?php echo $group['group']; ?></h6>

<!--Get the distinct race rows for each group-->
<?php $races = $conn->query("SELECT DISTINCT `race` FROM `savedRaces` WHERE `group` = ".$group['group']) or die($conn->error());
while ($race = $races->fetch_assoc()) : ?>

<h6>Race <?php echo $race['race']; ?></h6>

<!--Get the number of nodes to loop through-->
<?php $nodes = $conn->query("SELECT `node` FROM `nodes` WHERE 1") or die($conn->error());
while ($node = $nodes->fetch_assoc()) : ?>

<div class="delta5-margin delta5-float">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Pilot</th>
		<th><?php echo $node['node']; ?></th>
	</tr>
</thead>
<tbody>

<!--Get the laps to loop through-->
<?php $laps = $conn->query("SELECT `lap`, `min`, `sec`, `milliSec` FROM `savedRaces` WHERE `group` = ".$group['group']." AND `race` = ".$race['race']." AND `pilot` = ".$node['node']) or die($conn->error());
while ($lap = $laps->fetch_assoc()) : ?>

<tr>
	<td><?php echo $lap['lap']; ?></td>
	<td><?php echo $lap['min'].':'.$lap['sec'].':'.sprintf('%03d',$lap['milliSec']); ?></td>
</tr>

<?php endwhile ?>

</tbody>
</table>
</div>

<?php endwhile ?> <!--Node end-->

<div style="clear: both;"></div>

<?php endwhile ?> <!--Race end-->

<?php endwhile ?> <!--Group end-->
