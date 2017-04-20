<html>
<head>
<meta charset="UTF-8" />
<title>Settings - Delta5 VTX Timer</title>
<style>
body{
	background-color: black;
}
.datagrid1 { width: 100% }
.datagrid1 table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid1 {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #006699; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid1 table td, 
.datagrid1 table th { padding: 3px 10px; }
.datagrid1 table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #006699), color-stop(1, #00557F) );background:-moz-linear-gradient( center top, #006699 5%, #00557F 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#006699', endColorstr='#00557F');background-color:#006699; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #0070A8; } 
.datagrid1 table thead th:first-child { border: none; }
.datagrid1 table tbody td { color: #00496B; border-left: 1px solid #00557F;font-size: 12px;font-weight: normal; }
.datagrid1 table tbody .alt td { background: #E1EEF4; color: #00496B; }
.datagrid1 table tbody td:first-child { border-left: none; }
.datagrid1 table tbody tr:last-child td { border-bottom: none; }

.datagrid2 { width: 100% }
.datagrid2 table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid2 {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #991821; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid2 table td, 
.datagrid2 table th { padding: 3px 10px; }
.datagrid2 table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #991821), color-stop(1, #80141C) );background:-moz-linear-gradient( center top, #991821 5%, #80141C 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#991821', endColorstr='#80141C');background-color:#991821; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #80141C; } 
.datagrid2 table thead th:first-child { border: none; }
.datagrid2 table tbody td { color: #80141C; border-left: 1px solid #80141C;font-size: 12px;font-weight: normal; }
.datagrid2 table tbody .alt td { background: #F7CDCD; color: #80141C; }
.datagrid2 table tbody td:first-child { border-left: none; }
.datagrid2 table tbody tr:last-child td { border-bottom: none; }

.datagrid3 { width: 100% }
.datagrid3 table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid3 {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #36752D; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid3 table td, 
.datagrid3 table th { padding: 3px 10px; }
.datagrid3 table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #36752D), color-stop(1, #275420) );background:-moz-linear-gradient( center top, #36752D 5%, #275420 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#36752D', endColorstr='#275420');background-color:#36752D; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #36752D; } 
.datagrid3 table thead th:first-child { border: none; }
.datagrid3 table tbody td { color: #275420; border-left: 1px solid #C6FFC2;font-size: 12px;font-weight: normal; }
.datagrid3 table tbody .alt td { background: #DFFFDE; color: #275420; }
.datagrid3 table tbody td:first-child { border-left: none; }
.datagrid3 table tbody tr:last-child td { border-bottom: none; }

.datagrid4 { width: 100% }
.datagrid4 table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid4 {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #652299; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid4 table td, 
.datagrid4 table th { padding: 3px 10px; }
.datagrid4 table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #652299), color-stop(1, #4D1A75) );background:-moz-linear-gradient( center top, #652299 5%, #4D1A75 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#652299', endColorstr='#4D1A75');background-color:#652299; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #714399; } 
.datagrid4 table thead th:first-child { border: none; }
.datagrid4 table tbody td { color: #4D1A75; border-left: 1px solid #E7BDFF;font-size: 12px;font-weight: normal; }
.datagrid4 table tbody .alt td { background: #F4E3FF; color: #4D1A75; }
.datagrid4 table tbody td:first-child { border-left: none; }
.datagrid4 table tbody tr:last-child td { border-bottom: none; }

.datagrid5 { width: 100% }
.datagrid5 table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid5 {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #A65B1A; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid5 table td, 
.datagrid5 table th { padding: 3px 10px; }
.datagrid5 table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #FFB029), color-stop(1, #EDA426) );background:-moz-linear-gradient( center top, #FFB029 5%, #EDA426 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#FFB029', endColorstr='#EDA426');background-color:#FFB029; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #BF691E; } 
.datagrid5 table thead th:first-child { border: none; }
.datagrid5 table tbody td { color: #7F4614; border-left: 1px solid #D9CFB8;font-size: 12px;font-weight: normal; }
.datagrid5 table tbody .alt td { background: #F0E5CC; color: #7F4614; }
.datagrid5 table tbody td:first-child { border-left: none; }
.datagrid5 table tbody tr:last-child td { border-bottom: none; }

.datagrid6 { width: 100% }
.datagrid6 table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid6 {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #8C8C8C; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid6 table td, 
.datagrid6 table th { padding: 3px 10px; }
.datagrid6 table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #8C8C8C), color-stop(1, #7D7D7D) );background:-moz-linear-gradient( center top, #8C8C8C 5%, #7D7D7D 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#8C8C8C', endColorstr='#7D7D7D');background-color:#8C8C8C; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #A3A3A3; } 
.datagrid6 table thead th:first-child { border: none; }
.datagrid6 table tbody td { color: #7D7D7D; border-left: 1px solid #DBDBDB;font-size: 12px;font-weight: normal; }
.datagrid6 table tbody .alt td { background: #EBEBEB; color: #7D7D7D; }
.datagrid6 table tbody td:first-child { border-left: none; }.datagrid table tbody tr:last-child td { border-bottom: none; }
</style>

<?php
if (isset($_POST['setupData'])) {exec("sudo python /home/pi/VTX/setupData.py"); }
if (isset($_POST['startComms'])) {exec("sudo python /home/pi/VTX/startComms.py"); }
if (isset($_POST['stopComms'])) {exec("sudo python /home/pi/VTX/stopComms.py");	}

if (isset($_POST['node1rssiTriggerSet']))	{exec("sudo python /home/pi/VTX/rssiTrigger.py 1 8 set"); }
if (isset($_POST['node1rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 1 8 dec"); }
if (isset($_POST['node1rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 1 8 inc"); }
if (isset($_POST['node2rssiTriggerSet']))	{exec("sudo python /home/pi/VTX/rssiTrigger.py 2 10 set"); }
if (isset($_POST['node2rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 2 10 dec"); }
if (isset($_POST['node2rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 2 10 inc"); }
if (isset($_POST['node3rssiTriggerSet']))	{exec("sudo python /home/pi/VTX/rssiTrigger.py 3 12 set"); }
if (isset($_POST['node3rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 3 12 dec"); }
if (isset($_POST['node3rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 3 12 inc"); }
if (isset($_POST['node4rssiTriggerSet']))	{exec("sudo python /home/pi/VTX/rssiTrigger.py 4 14 set"); }
if (isset($_POST['node4rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 4 14 dec"); }
if (isset($_POST['node4rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 4 14 inc"); }
if (isset($_POST['node5rssiTriggerSet']))	{exec("sudo python /home/pi/VTX/rssiTrigger.py 5 16 set"); }
if (isset($_POST['node5rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 5 16 dec"); }
if (isset($_POST['node5rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 5 16 inc"); }
if (isset($_POST['node6rssiTriggerSet']))	{exec("sudo python /home/pi/VTX/rssiTrigger.py 6 18 set"); }
if (isset($_POST['node6rssiTriggerDec'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 6 18 dec"); }
if (isset($_POST['node6rssiTriggerInc'])) {exec("sudo python /home/pi/VTX/rssiTrigger.py 6 18 inc"); }
?>
</head>

<body>

<p><a href="index.php">Races</a> | <a href="pilots.php">Pilots</a> | <a href="groups.php">Groups</a> | <a href="manage.php">Manage</a> | <a href="settings.php">Settings</a></p>

<img src="/images/delta5fpv.jpg">

<form method="post">
<button name="setupData" style="height:40px; width:100px">Setup Data</button>&nbsp;
<button name="startComms" style="height:40px; width:100px">Start Comms</button>&nbsp;
<button name="stopComms" style="height:40px; width:100px">Stop Comms</button>&nbsp;
<br>
<br>
<button name="node1rssiTriggerSet" style="height:40px; width:80px">Node 1 Trigger</button>&nbsp;
<button name="node2rssiTriggerSet" style="height:40px; width:80px">Node 2 Trigger</button>&nbsp;
<button name="node3rssiTriggerSet" style="height:40px; width:80px">Node 3 Trigger</button>&nbsp;
<button name="node4rssiTriggerSet" style="height:40px; width:80px">Node 4 Trigger</button>&nbsp;
<button name="node5rssiTriggerSet" style="height:40px; width:80px">Node 5 Trigger</button>&nbsp;
<button name="node6rssiTriggerSet" style="height:40px; width:80px">Node 6 Trigger</button>&nbsp;
<br>
<button name="node1rssiTriggerDec" style="height:20px; width:38px">-5</button>
<button name="node1rssiTriggerInc" style="height:20px; width:38px">+5</button>&nbsp;
<button name="node2rssiTriggerDec" style="height:20px; width:38px">-5</button>
<button name="node2rssiTriggerInc" style="height:20px; width:38px">+5</button>&nbsp;
<button name="node3rssiTriggerDec" style="height:20px; width:38px">-5</button>
<button name="node3rssiTriggerInc" style="height:20px; width:38px">+5</button>&nbsp;
<button name="node4rssiTriggerDec" style="height:20px; width:38px">-5</button>
<button name="node4rssiTriggerInc" style="height:20px; width:38px">+5</button>&nbsp;
<button name="node5rssiTriggerDec" style="height:20px; width:38px">-5</button>
<button name="node5rssiTriggerInc" style="height:20px; width:38px">+5</button>&nbsp;
<button name="node6rssiTriggerDec" style="height:20px; width:38px">-5</button>
<button name="node6rssiTriggerInc" style="height:20px; width:38px">+5</button>&nbsp;
</form>

<div id="managedata"></div>

<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
<script type="text/javascript">
$(document).ready(function() {
	setInterval(function () {
		$('#managedata').load('managedata.php')
	}, 1000);
});
</script>

</body>
</html>
