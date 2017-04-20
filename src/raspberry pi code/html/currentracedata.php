<?php 
echo '<table border = 0 cellpadding = 10><tr>';

echo "<td valign=top>";
echo "<font color=white><b>Pilot 1-5685</b></font>";
echo '<div class="datagrid1">';
echo "<table><thead><tr><th>Lap</th><th>Time</th></tr></thead>";
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM currentrace WHERE pilot= '1'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>' . $row["lap"]  . '</td><td> '. $row["min"] . ':'. $row["sec"] . ':'. $row["millisec"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";
echo "</td>";

echo "<td valign=top>";
echo "<font color=white><b>Pilot 2-5760</b></font>";
echo '<div class="datagrid2">';
echo "<table><thead><tr><th>Lap</th><th>Time</th></tr></thead>";
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM currentrace WHERE pilot= '2'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>' . $row["lap"]  . '</td><td> '. $row["min"] . ':'. $row["sec"] . ':'. $row["millisec"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";
echo "</td>";

echo "<td valign=top>";
echo "<font color=white><b>Pilot 3-5800</b></font>";
echo '<div class="datagrid3">';
echo "<table><thead><tr><th>Lap</th><th>Time</th></tr></thead>";
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM currentrace WHERE pilot= '3'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>' . $row["lap"]  . '</td><td> '. $row["min"] . ':'. $row["sec"] . ':'. $row["millisec"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";
echo "</td>";

echo "<td valign=top>";
echo "<font color=white><b>Pilot 4-5860</b></font>";
echo '<div class="datagrid4">';
echo "<table><thead><tr><th>Lap</th><th>Time</th></tr></thead>";
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM currentrace WHERE pilot= '4'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>' . $row["lap"]  . '</td><td> '. $row["min"] . ':'. $row["sec"] . ':'. $row["millisec"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";
echo "</td>";

echo "<td valign=top>";
echo "<font color=white><b>Pilot 5-5905</b></font>";
echo '<div class="datagrid5">';
echo "<table><thead><tr><th>Lap</th><th>Time</th></tr></thead>";
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM currentrace WHERE pilot= '5'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>' . $row["lap"]  . '</td><td> '. $row["min"] . ':'. $row["sec"] . ':'. $row["millisec"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";
echo "</td>";

echo "<td valign=top>";
echo "<font color=white><b>Pilot 6-5645</b></font>";
echo '<div class="datagrid6">';
echo "<table><thead><tr><th>Lap</th><th>Time</th></tr></thead>";
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM currentrace WHERE pilot= '6'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>' . $row["lap"]  . '</td><td> '. $row["min"] . ':'. $row["sec"] . ':'. $row["millisec"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";
echo "</td>";

echo "</tr></table>";
?>
