# Raspberry Pi Referencia y Notas

### Acceso Remoto SSH (Solo Terminal)

https://www.raspberrypi.org/documentation/remote-access/ssh/

### Acceso Remoto VNC (Escritorio Remoto GUI)

https://www.raspberrypi.org/documentation/remote-access/vnc/README.md

### Samba Share para redes de Windows

Instalar Samba
```
$ sudo apt-get install samba samba-common-bin
```
Abrir el config
```
$ sudo leafpad /etc/samba/smb.conf
```
Establezca lo siguiente, descomente si es necesario
```
workgroup = WORKGROUP
wins support = yes
```
Agregar esto al final de config
```
[pihome]
   comment= Pi Home
   path=/home/pi
   browseable=Yes
   writeable=Yes
   only guest=no
   create mask=0777
   directory mask=0777
   public=no
```
Establecer la contraseña de usuario Pi
```
$ sudo smbpasswd -a pi
```

### Instalación de Github
```
$ sudo apt-get install git
```

### Punto de Acceso Inalàmbrico
[Install and configure dnsmasq and hostapd](https://github.com/SurferTim/documentation/blob/6bc583965254fa292a470990c40b145f553f6b34/configuration/wireless/access-point.md)

Completar las instrucciones también permitirá que el AP enrute el tráfico a la conexión por cable (suponiendo que la conexión por cable tenga internet)

Si bien algunos modelos de Raspberry Pi tienen redes inalámbricas integradas, no se recomienda para la mayoría de los usuarios del temporizador. La conexión inalámbrica interna tiene un alcance deficiente y colocar el temporizador en el suelo (que es común) o dentro de un escudo de RF direccional (necesario para muchos espacios interiores) reducirá aún más su capacidad. En su lugar, use un módulo WiFi externo o conecte el Pi a un enrutador inalámbrico independiente.
