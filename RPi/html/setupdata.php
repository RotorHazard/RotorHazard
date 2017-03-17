<?php 
echo '<div class="datagrid">';
echo "<table><thead><tr><th>Node</th><th>Trigger</th></tr></thead>";

$conn = new mysqli('localhost', 'root', 'delta5fpv', 'vtx');
if ($conn->connect_error) {
	die("Connection error: " . $conn->connect_error);
}
$result = $conn->query("SELECT * FROM setup WHERE ID = '1'");
if ($result->num_rows > 0) {

	while ($row = $result->fetch_assoc()) {
		echo '<tr><td>Node 1 - 5685</td><td>' . $row["trig1"]  . '</td></tr><tr><td>Node 2 - 5760</td><td> '. $row["trig2"] . '</td></tr><tr><td>Node 3 - 5800</td><td> '. $row["trig3"] . '</td></tr><tr><td>Node 4 - 5860</td><td> '. $row["trig4"] . '</td></tr><tr><td>Node 5 - 5905</td><td> '. $row["trig5"] . '</td></tr><tr><td>Node 6 - 5645</td><td> '. $row["trig6"] . '</td></tr>';
	}
}
echo "</table>";
echo "</div>";


?>
