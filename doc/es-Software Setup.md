#Instrucciones de configuración de software

El componente de software central del sistema RotorHazard es su servidor, escrito en Python, que opera sus funciones y sirve páginas web para los navegadores. En una configuración estándar, el servidor se ejecuta en un RaspberryPi. (También es posible ejecutar RotorHazard en otros tipos de hardware; consulte el[Other Operating Systems](#otheros) section below.)

##Instalar sistema (Raspberry Pi)
Nota: Muchos de los comandos de configuración a continuación requieren que Raspberry Pi tenga acceso a Internet.
Comience instalando Raspbian, siguiendo las instrucciones oficiales aquí: https://www.raspberrypi.org/downloads/raspbian/. Puede usar Desktop o Lite.

Configure las opciones de interfaz en la Raspberry Pi.
Abra una ventana de Terminal e ingrese el siguiente comando:
```
sudo raspi-config
```
Seleccione Opciones de Interfaz y habilite: SSH, SPI y I2C.

Actualice el sistema (esto puede tardar unos minutos):
```
sudo apt-get update && sudo apt-get upgrade
```

Instale Python y los drivers de Python para GPIO.
```
sudo apt-get install python-dev python-rpi.gpio libffi-dev python-smbus build-essential python-pip git scons swig
```

Instale la interfaz de la función en Python
```
sudo pip install cffi
```

Actualice el baudrate de puerto i2C
```
sudo nano /boot/config.txt
```
Añada las siguientes líneas al final del archivo config.txt:
```
dtparam=i2c_baudrate=75000
core_freq=250
```
Guarde y salga del archivo con Ctrl-X

Instale el código RotorHazard en '/ home / pi /' en la Raspberry Pi de la siguiente manera: Vaya a [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) para el proyecto y tenga en cuenta el código de versión. En los siguientes comandos, reemplace las dos apariciones de "1.2.3" con el código de la versión actual e ingrese los comandos:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
```

Instale las dependencias del servidor RotorHazard (sea paciente, este comando puede tardar unos minutos):
```
cd ~/RotorHazard/src/server
sudo pip install -r requirements.txt
```

Actualizar permisos en la carpeta de trabajo:
```
cd ~/RotorHazard/src
sudo chmod 777 server
```

* Nota: Si RotorHazard ya está instalado, consulte el [Updating an existing installation](#update) sección abajo.*

## Instalar el Código en los Nodo Receptores (Arduinos)
Requiere Arduino 1.8 o superior. Descárguelo de https://www.arduino.cc/en/Main/Software

* El código de nodo y la versión del servidor deben coincidir. Utilice el código 'nodo' incluido con el código del servidor que descargó anteriormente; no descargue un archivo diferente directamente desde GitHub. *

El código de nodo se puede editar y construir utilizando el[Eclipse IDE](https://www.eclipse.org/eclipseide/) y el "[Eclipse C++ IDE for Arduino](https://marketplace.eclipse.org/content/eclipse-c-ide-arduino)"plugin (o la forma tradicional usando el IDE de Arduino). En Eclipse, el proyecto de código de nodo se puede cargar a través de "Archivo | Abrir proyectos desde el sistema de archivos ..."

Edite el archivo 'src / node / config.h' y configure el valor '#define NODE_NUMBER' para cada nodo antes de cargarlo. Para el primer nodo, configure NODE_NUMBER en 1, para el segundo configúrelo en 2, etc.

```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```
También se puede configurar de manera automática los nodos mediante la conexión a tierra de estos pines de los Arduinos. Establezca NODE_NUMBER en 0, luego empalme estos pines a tierra (GND):

nodo #1: GND a pin D5<br/>
nodo #2: GND a pin D6<br/>
nodo #3: GND a pin D7<br/>
nodo #4: GND a pin D8<br/>
nodo #5: GND a pin D5 y pin D4<br/>
nodo #6: GND a pin D6 y pin D4<br/>
nodo #7: GND a pin D7 y pin D4<br/>
nodo #8: GND a pin D8 y pin D4<br/>

## Instalar Componentes opcionales
### Soporte WS2812b LED
Los controles de los LED ws2812b se proporcionan en el siguiente proyecto:
https://github.com/jgarff/rpi_ws281x

Clone el repositorio en la Pi e inicie Scons:
```
cd ~
sudo git clone https://github.com/jgarff/rpi_ws281x.git
cd rpi_ws281x
sudo scons
```

Instale la bilblioteca Python:
```
cd python
sudo python setup.py install
```

### Sensor de Voltage/Current INA219
La interfaz ina219 se proporciona en el siguiente proyecto:
https://github.com/chrisb2/pi_ina219

Clone el repositorio en la Pi:
```
cd ~
sudo git clone https://github.com/chrisb2/pi_ina219.git
cd pi_ina219
```
Instale la biblioteca Python:
```
sudo python setup.py install
```

### Sensor de Temperatura BME280
La interfaz bme280 se proporciona en el siguiente proyecto:
https://github.com/rm-hull/bme280

Clone el repositorio en la Pi:
```
cd ~
sudo git clone https://github.com/rm-hull/bme280.git
cd bme280
```
Instale la biblioteca Python:
```
sudo python setup.py install
```

### Soporte Java
Java permite el cálculo de las puntuaciones de IMD. Si comenzó con RASPBIAN WITH DESKTOP, este paso no debería ser necesario ya que Java está instalado de manera predeterminada. De otra manera:
```
sudo apt-get install openjdk-8-jdk
```

## Preparar el Sistema
### Reiniciar el Sistema
Después de realizar los pasos de configuración anteriores, el sistema debe reiniciarse ingresando lo siguiente:
```
sudo reboot
```

### Arrancando el Sistema

Las siguientes instrucciones iniciarán el servidor web en la raspberryPi, permitiendo el control total y la configuración del sistema para lanzar carreras y guardar los tiempos de vuelta.

#### Arranque Manual
Abra un terminal y escriba lo siguiente:
```
cd ~/RotorHazard/src/server
python server.py
```
El servidor se puede parar pulsando Ctrl+c

#### Arranque de inicio
Cree un servicio
```
sudo nano /lib/systemd/system/rotorhazard.service
```
con el siguiente contenido:
```
[Unit]
Description=RotorHazard Server
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/RotorHazard/src/server
ExecStart=/usr/bin/python server.py

[Install]
WantedBy=multi-user.target
```
Guarde y salga (CTRL-X, Y, ENTER).

Actualice los permisos.
```
sudo chmod 644 /lib/systemd/system/rotorhazard.service
```

Inicio con los comandos de arranque.
```
sudo systemctl daemon-reload
sudo systemctl enable rotorhazard.service
sudo reboot
```

### Apagando el Sistema
El apagado del sistema siempre debe realizarse antes de desconectar la alimentación, ya sea haciendo clic en el botón 'Apagar' en la página 'Configuración' o ingresando lo siguiente en un terminal:
```
sudo shutdown now
```

<a id="update"></a>
### Actualizar una instalación existente

Antes de actualizar, se debe detener cualquier servidor RotorHazard que se esté ejecutando actualmente. Si se instala como un servicio, se puede detener con un comando como: `sudo systemctl stop rotorhazard`

Para actualizar una instalación existente de RotorHazard: vaya a [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) para el proyecto y tenga en cuenta el código de versión. En los siguientes comandos, reemplace las dos apariciones de "1.2.3" con el código de la versión actual e ingrese los comandos:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
La instalación anterior termina en el directorio 'RotorHazard.old', que se puede eliminar o mover.

Las dependencias del servidor RotorHazard también deben actualizarse (tenga paciencia, este comando puede tardar unos minutos):
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```
<br/>

-----------------------------

<a id="otheros"></a>
### Otros sistemas operativos

El servidor RotorHazard puede ejecutarse en cualquier computadora con un sistema operativo que admita Python. En estas configuraciones alternativas, uno o más nodos de hardware se pueden conectar a través de USB; consulte [doc/USB Nodes.md](USB%20Nodes.md) para más información. El servidor también puede ejecutarse utilizando nodos simulados.

To install the RotorHazard server on these systems:

1. Si el ordenador aún no tiene Python instalado, descargue e instale Python versión 2.7 de https://www.python.org/downloads. Para verificar si Python está instalado, abra un símbolo del sistema e ingrese ```python --version```

1. Desde el RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), descargar el archivo "Source code (zip)".

1. Descomprima el archivo descargado en un directorio (también conocido como carpeta) en el ordenador.

1. Abra un símbolo del sistema y navegue hasta el directorio `` src / server`` en los archivos RotorHazard (usando el comando 'cd').

1. Instale las dependencias del servidor RotorHazard utilizando el archivo 'require.txt'. En un sistema Windows, el comando a usar probablemente será: ```python -m pip install -r requirements.txt```<br/>Tenga en cuenta que este comando puede requerir acceso de administrador al ordenador, y el comando puede tardar unos minutos en finalizar)

Para ejecutar el servidor RotorHazard en estos sistemas:

1. Abra un símbolo del sistema y navegue hasta el directorio ```src/server``` en los archivos RotorHazard (si aún no está allí).

1. Teclee: ```python server.py```

1. Si el servidor se inicia correctamente, debería ver varios mensajes de registro, incluido uno como este:
    ```
    Running http server at port 5000
    ```

1. El servidor se puede detener presionando Ctrl+C

Si los nodos de hardware están conectados a través de USB, deberán configurarse en la sección "SERIAL_PORTS" en el archivo de configuración "src / server / config.json" (consulte [doc/USB Nodes.md](USB%20Nodes.md) para detalles).

Si no hay configurados nodos de hardware, el servidor funcionará utilizando nodos simulados (simulados). En este modo, se puede explorar y probar la interfaz web-GUI.

Para ver la interfaz web-GUI, abra un navegador web e ingrese en la barra de direcciones: ```localhost:5000``` (Si el valor HTTP_PORT en la configuración ha cambiado, use ese valor en lugar de 5000). Si el servidor se está ejecutando, debería aparecer la página principal de RotorHazard. Tenga en cuenta que las páginas reservadas para el director de carrera (Administrador / Configuración) están protegidas con contraseña con el nombre de usuario y la contraseña especificados en la configuración.

<br/>

-----------------------------

Vea también:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/User Guide.md](User%20Guide.md)
