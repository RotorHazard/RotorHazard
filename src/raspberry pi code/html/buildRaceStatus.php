<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the system status variables-->
<?php $results = $conn->query("SELECT `raceStatus` FROM `status`") or die($conn->error());
$status = $results->fetch_assoc(); ?>

<!--Build system status table-->
<div class="delta5-margin">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 140px;">
<tbody>
<tr>
	<td>Race:</td>
	<td>
		<?php if ($status['raceStatus'] == 0) { echo "Stopped"; }
		else { echo "Started"; } ?>
	</td>
</tr>
</tbody>
</table>
</div>
