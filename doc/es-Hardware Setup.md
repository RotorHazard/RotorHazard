# Instrucciones de Configuración del Hardware

## Lista de componentes

### Nodo/s del receptor (esta lista forma un nodo, pero se pueden montar hasta ocho)
* 1 x [Arduino Nano](https://www.ebay.com/sch/i.html?_nkw=Arduino+Nano+V3.0+16M+5V+ATmega328P)
* 1 x [RX5808 module](https://www.banggood.com/search/rx5808-module.html) con el mod SPI (se sabe que los módulos con el código de fecha 20120322 funcionan)
* 3 resistencias x 1k ohm 
* 1 resistencia x 100k ohm
* Cable de silicona: medida 26 AWG y 30 AWG

### Componentes del Sistema
* 1 x Raspberry Pi3 (los usuarios de Pi2 han reportado problemas con múltiples nodos conectados)
* 8 GB (mínimo) Micro SD Card
* Cable de silicona de 26 AWG y 30 AWG (para cablear cada nodo del receptor)
* Carcasa 3D o similar para alojar todos los componentes
* Fuente de alimentación de 5V, de 3 amperios como mínimo (o fuente de alimentación de 12V si se utilizan reguladores a bordo)

### Componentes adicionales
* Blindaje RF (ver debajo)

### Componentes Opcionales
* Cable Ethernet, 30m o más
* Cable de corriente de exterior, 30 metros o más
* Enrutador de red
* Ordenador portáti / Tablet pc
* ws2812b LEDs

## Configuración del Hardware

### Receptores de vídeo RX5808 
Asegúrese de que sus receptores sean compatibles con SPI. * La mayoría de los módulos RX5808 a la venta ya llegan con SPI habilitado. * Si no lo hacen, modifique los receptores RX5808 para habilitar el soporte SPI de la siguiente manera:

Retire el escudo del RX5808, el escudo normalmente está sujeto por unos pocos puntos de soldadura alrededor de los bordes. Use una mecha de soldadura para eliminar la soldadura y liberar el escudo del receptor. Tenga cuidado de no dañar las almohadillas de tierra en el receptor. Por lo general, hay pequeños agujeros alrededor del borde que puede usar para ayudar a empujar el escudo.

Retire la siguiente resistencia:
![RX5808 spi mod](img/rx5808-new-top.jpg)

Vuelva a soldar el escudo protector una vez haya retirado la resistencia.

### Nodos Receptores
Complete el cableado entre cada Arduino y RX5808.
![receiver node wiring](img/Receivernode.png)

Nota: También se puede construir y conectar un nodo receptor simple a través de USB -- vea [doc/USB Nodes.md](USB%20Nodes.md).

### Ensamblaje del Sistema
Complete las conexiones de cableado entre cada Arduino y la Raspberry Pi.

Nota: asegúrese de que todos los nodos del receptor y la Raspberry Pi estén vinculados a un negativo (GND) común; si no, los mensajes de i2c pueden corromperse.
![system wiring](img/D5-i2c.png)

### Agregar un blindaje direccional de RF
Un escudo de RF direccional mejora significativamente la capacidad del sistema para rechazar pases falsos. Esto permite a los operadores aumentar su sensibilidad o construir carreras que pasan más cerca de la puerta de sincronización. Construya un escudo direccional que deje una línea de visión abierta entre el temporizador y la puerta de sincronización, pero que bloquee o atenúe las señales de RF de otras direcciones. Las opciones más populares para lograr esto son:
* Coloque el sistema dentro de una caja de metal con un lado abierto, como una lata de munición, una lata de pintura, un cubo de metal o una caja de computadora. Se recomienda conectar este estuche a una toma de tierra eléctrica en el temporizador.
* Cava un hoyo en el suelo y coloca tu estuche dentro de él
* Cubra su carcasa del sistema con cinta de cobre

### Soporte LED WS2812b
Los pines en el cuadro verde son los que ya están en uso en el temporizador. Los pines en el cuadro rojo es donde se debe conectar la señal y la tierra de los LED ws2812b. Los LED requerirán una fuente de alimentación separada. Consulte el soporte de LED WS2812b en Configuración de software.
![led wiring](img/GPIO.jpg)

### Sensores adicionales
Se pueden conectar sensores (como BME280 e INA219) al bus I2C y a los pines de alimentación. Consulte los archivos '..._ sensor.py' en el directorio "src / interface" para ver ejemplos de implementación. Los sensores deben especificarse en el archivo "src / server / config.json": en la siguiente configuración de muestra, un sensor BME280 está configurado en la dirección I2C 0x76 (como "Clima") y los sensores INA219 están configurados en 0x40 y 0x41 .
```
    "SENSORS": {
            "i2c:0x76": {
                    "name": "Climate"
            },
            "i2c:0x40": {
                    "name": "Battery",
                    "max_current": 0.1
            },
            "i2c:0x41": {
                    "name": "Pi",
                    "max_current": 2
            }
    },
```

### Temporizadores múltiples
Se pueden conectar varios temporizadores RotorHazard entre sí (es decir, para temporización dividida y duplicación); consulte[doc/Cluster.md](Cluster.md).

-----------------------------

Vea también:<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/Software Setup.md](Software%20Setup.md)<br/>
[doc/User Guide.md](User%20Guide.md)
