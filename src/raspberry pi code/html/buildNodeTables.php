<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

# Get rssi values
$results = $conn->query("SELECT `rssi` FROM `nodesMem`") or die($conn->error());
$rssi = array();
while ($row = $results->fetch_assoc()) {
	$rssi[] = $row['rssi'];
}

# Get node info

$index = 0;
?>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Node</th>
		<th><?php echo $node['node']; ?></th>
	</tr>
</thead>
<tbody>
<tr>
	<td>Channel:</td>
	<td><?php
			echo $node['vtxChan'];
			echo " ";
			echo $node['vtxFreq'];
		?></td>
</tr>
<tr>
	<td>RSSI:</td>
	<td><?php echo $rssi[$index]; ?></td>
</tr>
<tr>
	<td>Trigger:</td>
	<td><?php echo $node['rssiTrigger']; ?></td>
</tr>
</tbody>
</table>
</div>

<?php
$index++;
endwhile
?>
