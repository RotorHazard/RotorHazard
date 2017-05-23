<!--Initial database connection-->
<?php $conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); } ?>

<!--Get vtx reference lookup-->
<?php $results = $conn->query("SELECT `vtxChan` FROM `vtxReference` ORDER BY `vtxChan` ASC") or die($conn->error());
$vtxReference = array();
while ($row = $results->fetch_assoc()) { $vtxReference[] = $row; } ?>

<!--Get pilot lookup-->
<?php $results = $conn->query("SELECT `pilot`, `callSign` FROM `pilots` ORDER BY `callSign` ASC") or die($conn->error());
$pilots = array();
while ($row = $results->fetch_assoc()) { $pilots[] = $row; } ?>

<!--Get the current group-->
<?php $results = $conn->query("SELECT `group` FROM `config`") or die($conn->error());
$group = $results->fetch_assoc() ?>

<!--Build the legend table first-->
<div class="delta5-margin delta5-float">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 80px;">
<tbody>
<tr>
	<td>Pilot</td>
</tr>
<tr>
	<td>Channel</td>
</tr>
<tr>
	<td>Trigger</td>
</tr>
</tbody>
</table>
</div>

<!--Get number of nodes to loop through-->
<?php $nodes = $conn->query("SELECT `node` FROM `nodes` WHERE 1") or die($conn->error());
while ($node = $nodes->fetch_assoc()) : ?>

<!--Build table-->
<div class="delta5-margin delta5-float">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp" style="width: 120px;">
<tbody>
<tr>
	<td>
	<form method="post">
		<select name="setPilot" onchange="this.form.submit()">
			<!--Display the current pilot-->
			<?php $results = $conn->query("SELECT * FROM `groups` WHERE `group` = ".$group['group']." AND `node` = ".$node['node']) or die($conn->error());
			$pilot = $results->fetch_assoc();
			$results = $conn->query("SELECT `callSign` FROM `pilots` WHERE `pilot` =".$pilot['pilot']) or die($conn->error());
			$pilotCallSign = $results->fetch_assoc(); ?>
			<option value="<?php echo $pilot['pilot']; ?>"><?php echo $pilotCallSign['callSign']; ?></option>
			<!--Build the list of pilots-->
			<?php for ($i = 0; $i < count($pilots); $i++) : ?>
			<option value="<?php echo $pilots[$i]['pilot']; ?>"><?php echo $pilots[$i]['callSign']; ?></option>
			<?php endfor ?>
		</select>
		<!--Node and group variables to know which channel to change-->
		<input name="nodeid" value="<?php echo $node['node']; ?>" type="hidden"/>
		<input name="groupid" value="<?php echo $group['group']; ?>" type="hidden"/>
	</form>
	</td>
</tr>
<tr>
	<td>
	<form method="post">
		<select name="setVtxChannel" onchange="this.form.submit()">
			<!--Display the current vtx channel-->
			<?php $results = $conn->query("SELECT `vtxChan` FROM `groups` WHERE `group` = ".$group['group']." AND `node` = ".$node['node']) or die($conn->error());
			$vtxChan = $results->fetch_assoc(); ?>
			<option value="<?php echo $vtxChan['vtxChan']; ?>"><?php echo $vtxChan['vtxChan']; ?></option>
			<!--Build the list of vtx channels-->
			<?php for ($i = 0; $i < count($vtxReference); $i++) : ?>
			<option value="<?php echo $vtxReference[$i]['vtxChan']; ?>"><?php echo $vtxReference[$i]['vtxChan']; ?></option>
			<?php endfor ?>
		</select>
		<!--Node and group variables to know which channel to change-->
		<input name="nodeid" value="<?php echo $node['node']; ?>" type="hidden"/>
		<input name="groupid" value="<?php echo $group['group']; ?>" type="hidden"/>
	</form>
	</td>
</tr>
<tr>
	<td>
	<form method="post">
		<!--Display the current trigger-->
		<?php $results = $conn->query("SELECT `rssiTrigger` FROM `groups` WHERE `group` = ".$group['group']." AND `node` = ".$node['node']) or die($conn->error());
		$rssiTrigger = $results->fetch_assoc(); ?>
		<input name="setRssiTrigger" onchange="this.form.submit()" value="<?php echo $rssiTrigger['rssiTrigger']; ?>" size="2">
		<!--Node and group variables to know which channel to change-->
		<input name="nodeid" value="<?php echo $node['node']; ?>" type="hidden"/>
		<input name="groupid" value="<?php echo $group['group']; ?>" type="hidden"/>
	</form>	
	</td>
</tr>
</tbody>
</table>
</div>

<?php endwhile ?>

<div style="clear: both;"></div>
