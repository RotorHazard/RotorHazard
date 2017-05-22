<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get rssi values-->
<?php $results = $conn->query("SELECT `rssi` FROM `nodesMem`") or die($conn->error());
$rssi = array();
while ($row = $results->fetch_assoc()) { $rssi[] = $row['rssi']; } ?>

<!--Get node info-->
<?php $results = $conn->query("SELECT * FROM `nodes` WHERE 1") or die($conn->error());
$index = 0; # For referencing rssi array
while ($node = $results->fetch_assoc()) :
?>

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
	<td>RSSI:</td>
	<td><?php echo $rssi[$index]; ?></td>
</tr>
</tbody>
</table>
</div>

<?php
$index++;
endwhile
?>

<div style="clear: both;"></div>
