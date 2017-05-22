<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the number of groups to loop through-->
<?php $groups = $conn->query("SELECT DISTINCT `group` FROM `groups`") or die($conn->error());
while ($group = $groups->fetch_assoc()) : ?>

<h6>Group <?php echo $group['group']; ?></h6>

<!--Get the number of nodes to loop through-->
<?php $nodes = $conn->query("SELECT `node` FROM `nodes` WHERE 1") or die($conn->error());
while ($node = $nodes->fetch_assoc()) : ?>


<div class="delta5-margin delta5-float">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Node</th>
		<th><?php echo $node['node']; ?></th>
	</tr>
</thead>
<tbody>
<tr>
	<td>Pilot</td>
	<td><?php
	$results = $conn->query("SELECT * FROM `groups` WHERE `group` = ".$group['group']." AND `node` = ".$node['node']) or die($conn->error());
	$pilot = $results->fetch_assoc();
	$results = $conn->query("SELECT `callSign` FROM `pilots` WHERE `pilot` =".$pilot['pilot']) or die($conn->error());
	$pilotCallSign = $results->fetch_assoc();
	echo $pilotCallSign['callSign'];
	?></td>
</tr>
<tr>
	<td>Channel</td>
	<td><?php echo $pilot['vtxChan']; ?></td>
</tr>
<tr>
	<td>Trigger</td>
	<td><?php echo $pilot['rssiTrigger']; ?></td>
</tr>
</tbody>
</table>
</div>

<?php endwhile ?>

<div style="clear: both;"></div>

<?php endwhile ?>
