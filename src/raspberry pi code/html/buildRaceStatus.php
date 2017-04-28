<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$setups = $conn->query("SELECT `raceStatus` FROM `setup`") or die($conn->error());

while ($setup = $setups->fetch_assoc()) :
?>

<h5>Race Status: 
<?php
if ($setup['raceStatus'] == 0) {
	echo "Stopped";
} else {
	echo "Racing!";
}
?>
</h5>

<?php endwhile ?>