<?php 
echo '<font color=white><b>Admin Data</b></font>';
echo '<table border = 0 cellpadding = 10><tr>';

echo '<td><div class="datagrid1"><table><thead><tr><th>Race</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM setup WHERE ID = '1'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>Node Comms</td><td>' . $row["commsStatus"]  . '</td></tr>';
		echo '<tr><td>Racing</td><td>' . $row["raceStatus"]  . '</td></tr>';
		echo '<tr><td>Min Lap Time</td><td>' . $row["minLapTime"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo '<td><div class="datagrid1"><table><thead><tr><th>Node 1</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM nodes WHERE ID = '1'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>channel</td><td>' . $row["channel"]  . '</td></tr>';
		echo '<tr><td>rssi</td><td>' . $row["rssi"]  . '</td></tr>';
		echo '<tr><td>rssiTrig</td><td>' . $row["rssiTrig"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo '<td><div class="datagrid2"><table><thead><tr><th>Node 2</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM nodes WHERE ID = '2'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>channel</td><td>' . $row["channel"]  . '</td></tr>';
		echo '<tr><td>rssi</td><td>' . $row["rssi"]  . '</td></tr>';
		echo '<tr><td>rssiTrig</td><td>' . $row["rssiTrig"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo '<td><div class="datagrid3"><table><thead><tr><th>Node 3</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM nodes WHERE ID = '3'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>channel</td><td>' . $row["channel"]  . '</td></tr>';
		echo '<tr><td>rssi</td><td>' . $row["rssi"]  . '</td></tr>';
		echo '<tr><td>rssiTrig</td><td>' . $row["rssiTrig"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo '<td><div class="datagrid4"><table><thead><tr><th>Node 4</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM nodes WHERE ID = '4'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>channel</td><td>' . $row["channel"]  . '</td></tr>';
		echo '<tr><td>rssi</td><td>' . $row["rssi"]  . '</td></tr>';
		echo '<tr><td>rssiTrig</td><td>' . $row["rssiTrig"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo '<td><div class="datagrid5"><table><thead><tr><th>Node 5</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM nodes WHERE ID = '5'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>channel</td><td>' . $row["channel"]  . '</td></tr>';
		echo '<tr><td>rssi</td><td>' . $row["rssi"]  . '</td></tr>';
		echo '<tr><td>rssiTrig</td><td>' . $row["rssiTrig"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo '<td><div class="datagrid6"><table><thead><tr><th>Node 6</th><th>Value</th></tr></thead>';
$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM nodes WHERE ID = '6'");
if ($result->num_rows > 0) {
	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>channel</td><td>' . $row["channel"]  . '</td></tr>';
		echo '<tr><td>rssi</td><td>' . $row["rssi"]  . '</td></tr>';
		echo '<tr><td>rssiTrig</td><td>' . $row["rssiTrig"]  . '</td></tr>';
	}
}
echo "</table></div></td>";

echo "</tr></table>";
?>
