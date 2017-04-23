<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }


$results = $conn->query("SELECT * FROM `vtxReference` WHERE 1");
$vtxReference = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$vtxReference[] = $row;
	echo $row[$index]['vtxNum'];
	$index++;
}

$nodes = $conn->query("SELECT * FROM `nodes` WHERE 1");

while ($node = $nodes->fetch_assoc()) :
?>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<tbody>
<tr>
	<td>
	<form method="post">
		<button <?php echo 'id="node'.$node['node'].'channelSet"'; ?> class="mdl-chip"><span class="mdl-chip__text">Channel</span></button>
		<ul class="mdl-menu mdl-js-menu mdl-js-ripple-effect" <?php echo 'for="node'.$node['node'].'channelSet"'; ?> >
			<li class="mdl-menu__item">E2 - 5860</li>
			<li class="mdl-menu__item">E2 - 5860</li>
			<li class="mdl-menu__item">E2 - 5860</li>
			<li class="mdl-menu__item">E2 - 5860</li>
		</ul>
	</form>
	</td>
</tr>
<tr>
	<td>
	<form method="post" action="">
	<button class="mdl-chip" name="rssiTrigger" value="Set"><span class="mdl-chip__text">Trigger</span></button><br>
	<button class="mdl-chip" name="rssiTrigger" value="Dec"><span class="mdl-chip__text">-5</span></button>
	<button class="mdl-chip" name="rssiTrigger" value="Zero"><span class="mdl-chip__text">0</span></button>
	<button class="mdl-chip" name="rssiTrigger" value="Inc"><span class="mdl-chip__text">+5</span></button>
	<input type="hidden" name="nodeid" value="<?php echo $node['node']; ?>"/>
	</form>
	</td>
</tr>
</tbody>
</table>
</div>

<?php endwhile ?>
