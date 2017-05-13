<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$setups = $conn->query("SELECT * FROM `setup`") or die($conn->error());

while ($setup = $setups->fetch_assoc()) :
?>


<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<tbody>
<tr>
	<td>System:</td>
	<td>
		<?php
		if ($setup['systemStatus'] == 0) {
			echo "Stopped";
		} else {
			echo "Started";
		}
		?>
	</td>
</tr>
<tr>
	<td>Race:</td>
	<td>
		<?php
		if ($setup['raceStatus'] == 0) {
			echo "Stopped";
		} else {
			echo "Started";
		}
		?>
	</td>
</tr>
<tr>
	<td>Min Lap Time:</td>
	<td>
		<?php echo $setup['minLapTime']; ?>
	</td>
</tr>
</tbody>
</table>


<?php endwhile ?>