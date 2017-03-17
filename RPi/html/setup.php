<html>
<head>
<meta charset="UTF-8" />
<title>SETUP - D5 VTX Timer</title>
<style>
body{
	background-color: black;
}

.datagrid { width: 25% }
.datagrid table { border-collapse: collapse; text-align: left; width: 100%; } 
.datagrid {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #006699; -webkit-border-radius: 10px; -moz-border-radius: 10px; border-radius: 10px; }
.datagrid table td, 
.datagrid table th { padding: 3px 10px; }
.datagrid table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #006699), color-stop(1, #00557F) );background:-moz-linear-gradient( center top, #006699 5%, #00557F 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#006699', endColorstr='#00557F');background-color:#006699; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #0070A8; } 
.datagrid table thead th:first-child { border: none; }
.datagrid table tbody td { color: #00496B; border-left: 1px solid #00557F;font-size: 12px;font-weight: normal; }
.datagrid table tbody .alt td { background: #E1EEF4; color: #00496B; }
.datagrid table tbody td:first-child { border-left: none; }
.datagrid table tbody tr:last-child td { border-bottom: none; }


</style>

<?php
if (isset($_POST['TRIGGER1']))
	{
	exec("sudo python /home/pi/VTX/trigger1.py");
	}
if (isset($_POST['DEC1']))
	{
	exec("sudo python /home/pi/VTX/trigdec1.py");
	}
if (isset($_POST['INC1']))
	{
	exec("sudo python /home/pi/VTX/triginc1.py");
	}
if (isset($_POST['TRIGGER2']))
	{
	exec("sudo python /home/pi/VTX/trigger2.py");
	}
if (isset($_POST['DEC2']))
	{
	exec("sudo python /home/pi/VTX/trigdec2.py");
	}
if (isset($_POST['INC2']))
	{
	exec("sudo python /home/pi/VTX/triginc2.py");
	}
if (isset($_POST['TRIGGER3']))
	{
	exec("sudo python /home/pi/VTX/trigger3.py");
	}
if (isset($_POST['DEC3']))
	{
	exec("sudo python /home/pi/VTX/trigdec3.py");
	}
if (isset($_POST['INC3']))
	{
	exec("sudo python /home/pi/VTX/triginc3.py");
	}
if (isset($_POST['TRIGGER4']))
	{
	exec("sudo python /home/pi/VTX/trigger4.py");
	}
if (isset($_POST['DEC4']))
	{
	exec("sudo python /home/pi/VTX/trigdec4.py");
	}
if (isset($_POST['INC4']))
	{
	exec("sudo python /home/pi/VTX/triginc4.py");
	}
if (isset($_POST['TRIGGER5']))
	{
	exec("sudo python /home/pi/VTX/trigger5.py");
	}
if (isset($_POST['DEC5']))
	{
	exec("sudo python /home/pi/VTX/trigdec5.py");
	}
if (isset($_POST['INC5']))
	{
	exec("sudo python /home/pi/VTX/triginc5.py");
	}
if (isset($_POST['TRIGGER6']))
	{
	exec("sudo python /home/pi/VTX/trigger6.py");
	}
if (isset($_POST['DEC6']))
	{
	exec("sudo python /home/pi/VTX/trigdec6.py");
	}
if (isset($_POST['INC6']))
	{
	exec("sudo python /home/pi/VTX/triginc6.py");
	}
?>
</head>
<body>

<img src="/images/delta5fpv.jpg"><p>
<form method="post">
<button name="TRIGGER1" style="height:50px; width:125px">Trigger 1</button>&nbsp;
<button name="TRIGGER2" style="height:50px; width:125px">Trigger 2</button>&nbsp;
<button name="TRIGGER3" style="height:50px; width:125px">Trigger 3</button>&nbsp;
<button name="TRIGGER4" style="height:50px; width:125px">Trigger 4</button>&nbsp;
<button name="TRIGGER5" style="height:50px; width:125px">Trigger 5</button>&nbsp;
<button name="TRIGGER6" style="height:50px; width:125px">Trigger 6</button>&nbsp;
<br>
<button name="DEC1" style="height:25px; width:60px">-5</button>
<button name="INC1" style="height:25px; width:60px">+5</button>&nbsp;
<button name="DEC2" style="height:25px; width:60px">-5</button>
<button name="INC2" style="height:25px; width:60px">+5</button>&nbsp;
<button name="DEC3" style="height:25px; width:60px">-5</button>
<button name="INC3" style="height:25px; width:60px">+5</button>&nbsp;
<button name="DEC4" style="height:25px; width:60px">-5</button>
<button name="INC4" style="height:25px; width:60px">+5</button>&nbsp;
<button name="DEC5" style="height:25px; width:60px">-5</button>
<button name="INC5" style="height:25px; width:60px">+5</button>&nbsp;
<button name="DEC6" style="height:25px; width:60px">-5</button>
<button name="INC6" style="height:25px; width:60px">+5</button>&nbsp;

</form>
<p>



<div id="show"></div>




<p>


<script type="text/javascript" src="/scripts/jquery-3.1.1.js"></script>
<script type="text/javascript">
$(document).ready(function() {
	setInterval(function () {
		$('#show').load('setupdata.php')
	}, 3000);
});
</script>


</body>
</html>
