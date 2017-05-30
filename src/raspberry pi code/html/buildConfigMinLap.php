<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the system status variables-->
<?php $results = $conn->query("SELECT `minLapTime` FROM `config`") or die($conn->error());
$config = $results->fetch_assoc(); ?>

<!--Build system status table-->
<div class="delta5-margin">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 140px;">
<tbody>
<tr>
	<td>Min Lap:</td>
	<td>
	<!--Create min lap time drop down options-->
	<form method="post">
		<select name="setMinLapTime" onchange="this.form.submit()">
			<option value="<?php echo $config['minLapTime']; ?>"><?php echo $config['minLapTime']; ?> sec</option>
			<!--Build the list of times-->
			<?php for ($i = 5; $i <= 30; $i += 5): ?>
			<option value="<?php echo $i ?>">
				<?php echo $i ?> sec
			</option>
			<?php endfor; ?>
		</select>
	</form>
	</td>
</tr>
</tbody>
</table>
</div>
