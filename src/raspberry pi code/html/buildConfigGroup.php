<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get the system status variables-->
<?php $results = $conn->query("SELECT `group` FROM `config`") or die($conn->error());
$config = $results->fetch_assoc(); ?>

<!--Build system status table-->
<div class="delta5-margin">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 140px;">
<tbody>
<tr>
	<td>Group:</td>
	<td>
	<!--Build the drop down selection to change the group-->
	<form method="post">
		<select name="setGroup" onchange="this.form.submit()">
			<!--Get groups list-->
			<?php $results = $conn->query("SELECT DISTINCT `group` FROM `groups` ORDER BY `group` ASC") or die($conn->error());
			$groups = array();
			while ($row = $results->fetch_assoc()) {
				$groups[] = $row;
			} ?>
			<!--Display the current group first-->
			<option value="<?php echo $config['group']; ?>"><?php echo $config['group']; ?></option>
			<!--Build the list of groups-->
			<?php for ($i = 0; $i < count($groups); $i++): ?>
			<option value="<?php echo $groups[$i]['group']; ?>">
				<?php echo $groups[$i]['group']; ?>
			</option>
			<?php endfor; ?>
		</select>
	</form>
	</td>
</tr>
</tbody>
</table>
</div>
