<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

# get the max laps for each pilot
$results = $conn->query("SELECT `pilot`, MAX(`lap`) AS `maxLap` FROM `currentLaps` GROUP BY `pilot` ORDER BY `pilot` ASC") or die($conn->error());
$maxLaps = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$maxLaps[] = $row;
	$index++;
}

# get the total race time for each pilot
$results = $conn->query("SELECT `pilot`, SUM(`min`)*60000 + SUM(`sec`)*1000 + SUM(`milliSec`) AS `totalTime` FROM `currentLaps` GROUP BY `pilot` ORDER BY `pilot` ASC") or die($conn->error());
$totalTime = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$totalTime[] = $row;
	$index++;
} 

# get the last lap for each pilot
$results = $conn->query("SELECT m1.* FROM `currentLaps` m1 LEFT JOIN `currentLaps` m2 ON (m1.pilot = m2.pilot AND m1.lap < m2.lap) WHERE m2.lap IS NULL;") or die($conn->error());
$lastLap = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$lastLap[] = $row;
	$index++;
}

# get the average lap time for each pilot
$results = $conn->query("SELECT `pilot`, AVG(`min`)*60000 + AVG(`sec`)*1000 + AVG(`milliSec`) AS `avgLap` FROM `currentLaps` GROUP BY `pilot` ORDER BY `pilot` ASC") or die($conn->error());
$avgLap = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$avgLap[] = $row;
	$index++;
} 

# get the fastest lap time for each pilot
$results = $conn->query("SELECT `pilot`, MAX(`min`*60000 + `sec`*1000 + `milliSec`) AS `fastLap` FROM `currentLaps` GROUP BY `pilot` ORDER BY `pilot` ASC") or die($conn->error());
$fastLap = array();
$index = 0;
while ($row = $results->fetch_assoc()) {
	$fastLap[] = $row;
	$index++;
}

# add all columns to the leaderboard
$leaderboard = array();
for ($i = 0; $i < count($maxLaps); $i++) {
	$leaderboard[] = array('pilot' => $maxLaps[$i]['pilot'], 'maxLap' => $maxLaps[$i]['maxLap'], 'totalTime' => $totalTime[$i]['totalTime'], 'lastMin' => $lastLap[$i]['min'], 'lastSec' => $lastLap[$i]['sec'], 'lastMilliSec' => $lastLap[$i]['milliSec'], 'avgLap' => $avgLap[$i]['avgLap'], 'fastLap' => $fastLap[$i]['fastLap']);
} 
#for ($i = 0; $i < count($leaderboard); $i++) {
#	echo '<p>Pilot: '.$leaderboard[$i]['pilot'].' maxLap: '.$leaderboard[$i]['maxLap'].' totalTime: '.$leaderboard[$i]['totalTime'].' ms</p>';
#} 

# sort by max lap then by quickest time
foreach ($leaderboard as $key => $row) {
	$maxLap[$key]  = $row['maxLap'];
	$totalTime[$key] = $row['totalTime'];
}
array_multisort($maxLap, SORT_DESC, $totalTime, SORT_ASC, $leaderboard);

#for ($i = 0; $i < count($leaderboard); $i++) {
#	echo '<p>Pilot: '.$leaderboard[$i]['pilot'].' maxLap: '.$leaderboard[$i]['maxLap'].' totalTime: '.$leaderboard[$i]['totalTime'].' ms</p>';
#} 


?>
<br>

<div class="mdl-cell mdl-cell--2-col">
<table class="delta5-table mdl-data-table mdl-js-data-table mdl-shadow--2dp">
<thead>
	<tr>
		<th>Position</th>
		<th>Pilot</th>
		<th>Laps</th>
		<th>Last Lap</th>
		<th>Behind</th>
		<th>Average</th>
		<th>Fastest</th>
	</tr>
</thead>
<tbody>

<?php
for ($i = 0; $i < count($leaderboard); $i++) :
?>
<tr>
	<td><?php echo $i+1 ?></td>
	<td><?php echo $leaderboard[$i]['pilot']; ?></td>
	<td><?php echo $leaderboard[$i]['maxLap']; ?></td>
	<td><?php echo $leaderboard[$i]['lastMin'].':'.$leaderboard[$i]['lastSec'].':'.$leaderboard[$i]['lastMilliSec']; ?></td>
	<td><?php
	$behind = $leaderboard[0]['maxLap']-$leaderboard[$i]['maxLap'];
	if ($behind == 0) {
		echo "-";
	} else {
		echo $behind;
	}
	?></td>
	<td><?php
	$avgMin = (int)($leaderboard[$i]['avgLap'] / 60000);
	$over = (int)($leaderboard[$i]['avgLap'] % 60000);
	$avgSec = (int)($over / 1000);
	$over = (int)($over % 1000);
	$avgMilliSec = $over;	
	echo $avgMin.':'.$avgSec.':'.$avgMilliSec;
	?></td>
	<td><?php
	$fastMin = (int)($leaderboard[$i]['fastLap'] / 60000);
	$over = (int)($leaderboard[$i]['fastLap'] % 60000);
	$fastSec = (int)($over / 1000);
	$over = (int)($over % 1000);
	$fastMilliSec = $over;	
	echo $fastMin.':'.$fastSec.':'.$fastMilliSec;
	?></td>
</tr>
<?php endfor ?>

</tbody>
</table>
</div>

