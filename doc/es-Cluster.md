# Racimo

Se pueden conectar cronos RotorHazard adicionales como unidades "esclavas", interconectadas a través de su conexión de red (es decir, WiFi). El modo predeterminado es 'temporizador' (para tiempo dividido), que permite colocar múltiples temporizadores alrededor de la pista para obtener tiempos de vuelta intermedios. También se admite un modo 'espejo', en el que el temporizador esclavo reflejará las acciones del maestro (por ejemplo, como un temporizador "solo LED" que muestra las acciones del maestro).

### Configuración

Se pueden configurar cronos adicionales (en 'src/server/config.json') en "GENERAL" con una entrada "ESCLAVOS" que contiene una lista de direcciones IP de los cronos esclavos en orden de seguimiento.

```
{
	"GENERAL": {
		... ,
		"SLAVES": ["192.168.1.2:5000", "192.168.1.3:5000"]
	}
}
```

Se pueden configurar opciones adicionales, por ejemplo:

```
{
	"GENERAL": {
		... ,
		"SLAVES": [{"address": "192.168.1.2:5000", "mode": "timer", "distance": 5}, {"address": "192.168.1.2:5000", "mode": "mirror"}],
		"SLAVE_TIMEOUT": 10
	}
}
```
* "address": La direccion IP y puerto para el crono esclavo.
* "mode": El modo en que actuará el crono (ya sea "timer" or "mirror").
* "distance": La distrancia desde la puerta anterior (utilizada para calcular la velocidad).

### Sincronización del Reloj

Es importante que todos los cronos tengan sus relojes sincronizados.
Puede usar NTP para hacer esto.

En todos los temporizadores:

	sudo apt-get install ntp

En el maestro, edite /etc/npd.conf y agregue las siguientes líneas similares a estas:

	restrict 192.168.123.0 mask 255.255.255.0
	broadcast 192.168.123.255
	
En los esclavos, edite /etc/npd.conf y agregue líneas similares a:

	server 192.168.123.1

En todos los cronos:

	sudo systemctl stop systemd-timesyncd
	sudo systemctl disable systemd-timesyncd
	sudo /etc/init.d/ntp restart

### Generador de números aleatorios

El generador de números aleatorios ayuda a mejorar la conectividad WiFi (mantiene la entropía para el cifrado). Active el RNG de hardware para mejorar la entropía disponible.

	sudo apt-get install rng-tools

Edite /etc/default/rng-tools y descomente la línea:

    HRNGDEVICE=/dev/hwrng

Luego, reinicie rng-tools con

    sudo service rng-tools restart

### Notas

Los tiempos parciales perdidos/incorrectos no tendrán impacto en la grabación de los tiempos de vuelta contados por el crono maestro.

Un esclavo también puede ser un maestro, pero las sub-divisiones no se propagan hacia arriba.

Si desea utilizar un racimo basado en Wi-Fi, puede encontrar instrucciones para configurar un punto de acceso (punto de acceso Wi-Fi) en
<https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md>.
También, lea <https://github.com/mr-canoehead/vpn_client_gateway/wiki/Configuring-the-Pi-as-a-WiFi-Access-Point>
y <https://superuser.com/questions/1263588/strange-issue-with-denyinterfaces-in-access-point-config>.
Específicamente, añada `denyinterfaces wlan0` a `/etc/dhcpcd.conf` y `sudo nano /etc/network/interfaces.d/wlan0`
para añadir

```
allow-hotplug wlan0
iface wlan0 inet static
	address 10.2.2.1
	netmask 255.255.255.0
	network 10.2.2.0
	broadcast 10.2.2.255
	post-up systemctl restart hostapd
```
para hacer que dhcpcd funcione mejor con hostapd.
