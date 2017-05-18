<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

# Get vtx reference lookup
$results = $conn->query("SELECT * FROM `vtxReference` ORDER BY `vtxChan` ASC") or die($conn->error());
$vtxReference = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$vtxReference[] = $row;
	$index++;
}

# Get node info
$nodes = $conn->query("SELECT * FROM `nodes` WHERE 1") or die($conn->error());

while ($node = $nodes->fetch_assoc()) :
?>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<tbody>
<tr>
	<td>
	<form method="post">
		<select name="vtxFrequency">
			<?php for ($i = 0; $i < count($vtxReference); $i++) : ?>
			<option value="<?php echo $vtxReference[$i]['vtxFreq']; ?>">
				<?php echo $vtxReference[$i]['vtxChan']; echo " "; echo $vtxReference[$i]['vtxFreq']; ?>
			</option>
			<?php endfor ?>
		</select>
		<button name="setVtxFrequency" class="mdl-chip"><span class="mdl-chip__text">Set</span></button>
		<input name="nodeid" value="<?php echo $node['node']; ?>" type="hidden"/>
	</form>
	</td>
</tr>
<tr>
	<td>
	<form method="post" action="">
		<button name="rssiTrigger" value="Set" class="mdl-chip"><span class="mdl-chip__text">Trigger</span></button><br>
		<button name="rssiTrigger" value="Dec" class="mdl-chip"><span class="mdl-chip__text">-5</span></button>
		<button name="rssiTrigger" value="Zero" class="mdl-chip"><span class="mdl-chip__text">0</span></button>
		<button name="rssiTrigger" value="Inc" class="mdl-chip"><span class="mdl-chip__text">+5</span></button>
		<input name="nodeid" value="<?php echo $node['node']; ?>" type="hidden"/>
	</form>
	</td>
</tr>
</tbody>
</table>
</div>

<?php endwhile ?>
