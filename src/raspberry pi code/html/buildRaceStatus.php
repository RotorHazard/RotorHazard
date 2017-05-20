<?php 
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {	die("Connection error: " . $conn->connect_error); }

$results = $conn->query("SELECT `raceStatus` FROM `status`") or die($conn->error());
$status = $results->fetch_assoc();
?>

<h5>Race Status: 
<?php
if ($status['raceStatus'] == 0) {
	echo "Stopped";
} else {
	echo "Racing!";
}
?>
</h5>
