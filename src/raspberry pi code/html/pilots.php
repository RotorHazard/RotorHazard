<html>
<head>
<meta charset="UTF-8" />
<title>Pilots - Delta5 VTX Timer</title>
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
</head>

<body>

<p><a href="index.php">Races</a> | <a href="pilots.php">Pilots</a> | <a href="groups.php">Groups</a> | <a href="manage.php">Manage</a> | <a href="settings.php">Settings</a></p>

<img src="/images/delta5fpv.jpg"><p>

</body>
</html>
