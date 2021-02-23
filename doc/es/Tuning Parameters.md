# Parámetros de calibración y ajuste del sensor

Cada nodo realiza un seguimiento de la intensidad de la señal (RSSI) en una frecuencia seleccionada y utiliza esta intensidad relativa para determinar si un transmisor está cerca de la puerta donde está alojado el crono. El sistema de sincronización RotorHazard le permite calibrar cada nodo individualmente para que pueda compensar el comportamiento y las diferencias de hardware en su sistema y en su entorno.

Un nodo puede estar *Cruzando* o *Despejado*. Si un nodo es *Despejado*, el sistema cree que no hay ningún dron cerca de la puerta del crono porque el RSSI es bajo. Si está *Cruzando*, el sistema cree que hay un transmisor pasando por la puerta de sincronización porque el RSSI es alto. Se registrará un pase de vuelta una vez que *Cruzando* haya finalizado y el sistema regrese a *Despejado*.

![Tuning Graph](../img/Tuning%20Graph-06.svg)<br />
_La señal RSSI durante una carrera aparece similar a este gráfico con muchos picos y bajadas visibles. A medida que el transmisor se acerca a la puerta de sincronización, la señal aumenta._

## Parámetros
Dos parámetros que afectan el estado *Cruzando*: *EnterAt* y *ExitAt*.

### EnterAt
El sistema cambiará a *Cruzando* cuando la señal RSSI suba o supere este nivel. Está indicado por una línea roja.

### ExitAt
El sistema cambiará a *Despejado* una vez que el valor de la señal RSSI caiga por debajo de este nivel. Está indicado por una línea naranja.

Entre *EnterAt* y *ExitAt*, el sistema seguirá estando *Cruzando* o *Despejado* dependiendo de su estado anterior.

![Sample RSSI Graph](../img/Sample%20RSSI%20Graph.svg)

### Modo de Calibrado

El modo de calibrado *Manual* siempre utilizará los valores *EnterAt* y *ExitAt* proporcionados por el usuario manualmente.

El modo de calibración *Adaptativo* utiliza los puntos definidos por el usuario a menos que haya carreras guardadas. Cuando existen carreras guardadas, el cambio entre series iniciará una búsqueda de datos de carreras anteriores para obtener los mejores valores de calibrado para usar en la próxima carrera. Estos valores se copian y reemplazan los valores actuales *EnterAt* y *ExitAt* para todos los nodos. Este modo mejora la calibración a medida que se guardan más carreras, si el director de carrera confirma los conteos de vueltas entrantes o los recalcula a través de la página *Mariscal*. Para que estos valores se vayan guardando tendremos que pinchar en REALIZAR CAMBIOS dentro de la página *Mariscal*

## Sintonización
Antes de sintonizar, encienda el temporizador y manténgalo en funcionamiento durante unos minutos para permitir que los módulos receptores se calienten. Los valores de RSSI tienden a aumentar en algunos puntos a medida que el temporizador se calienta.

Puede usar la página *Mariscal* para ajustar los valores visualmente. Recopile datos corriendo una carrera con un piloto en cada canal, luego guárdelo. Abra la página *Mariscal* y vea los datos de la carrera ajustando los puntos de entrada y salida hasta que el número de vueltas sea correcto. Guarde los puntos de entrada/salida en cada nodo para usarlos como calibrado para futuras carreras.

### Configurar el valor *EnterAt*
![Tuning Graph](../img/Tuning%20Graph-10.svg)

* Por debajo del pico de todos los cruces de puertas
* Por encima de cualquier pico cuando el transmisor no está cerca de la puerta
* Superior a *ExitAt*

### Configurar el valor *ExitAt*
![Tuning Graph](../img/Tuning%20Graph-11.svg)

* Debajo de los valles que ocurren durante un cruce de la puerta
* Por encima del valor más bajo visto durante cualquier vuelta
* Menor que *EnterAt*

Los valores ExitAt más cercanos a EnterAt permiten que el temporizador anuncie y muestre vueltas antes, pero puede hacer que se registren varias vueltas.

### Ejemplo de Sintonización
![Tuning Graph](../img/Tuning%20Graph-01.svg)<br />
_Se registran dos vueltas. La señal sube por encima de *EnterAt* y luego cae por debajo de *ExitAt* dos veces, una en cada pico. Dentro de estas dos ventanas cruzadas, el crono encuentra la señal más fuerte después del filtrado de ruido para usarla como el tiempo de vuelta registrado._

### Método de ajuste alternativo

Los botones *Capturar* pueden usarse para almacenar la lectura actual de RSSI como el valor *EnterAt* o *ExitAt* para cada nodo. Los valores también pueden ingresarse y ajustarse manualmente.

Encienda un quad en el canal correcto y llévelo muy cerca del crono durante unos segundos. Esto permitirá que el crono capture el valor máximo de señal RSSI para ese nodo. Esto debe hacerse para cada nodo/canal que se esté sintonizando. Se mostrará el valor pico.

#### EnterAt
Un buen punto de partida para *EnterAt* es capturar el valor con un quad a unos 1,5m – 3m (5–10 pies) del temporizador.

#### ExitAt
Un buen punto de partida para *ExitAt* es capturar el valor con un quad a unos 6m – 9m (20–30 pies) del temporizador.

## Notas
* Un valor bajo *ExitAt* aún puede proporcionar una sincronización precisa, pero el sistema esperará más tiempo antes de anunciar vueltas. Un retraso en el anuncio no afecta la precisión del temporizador.
* El ajuste *Tiempo mínimo de vuelta* se puede usar para evitar pases adicionales, pero puede enmascarar los cruces que se activan demasiado pronto. Se recomienda dejar el comportamiento en *Resaltar* en lugar de *Descartar*.
* Si tiene problemas de tiempo durante una carrera y los gráficos RSSI responden a la ubicación del transmisor, no pare la carrera. Guarde la carrera después de que se complete y visite la página *Mariscal*. Todo el historial RSSI se guarda y la carrera se puede volver a calcular con precisión con valores de ajuste actualizados.

## Solución de Problemas

### Vueltas Perdidas (Sistema generalmente *Despejado*)
![Tuning Graph](../img/Tuning%20Graph-04.svg)<br />
_Las vueltas no se registran si RSSI no llega a EnterAt._
* Bajar *EnterAt*

### Vueltas Perdidas (Sistema generalmente *Cruzando*)
![Tuning Graph](../img/Tuning%20Graph-05.svg)<br />
_Las vueltas fse fusionan si *ExitAt* es demasiado bajo porque el primer cruce de la vuelta nunca se completa._
* Subir *ExitAt*

### Se cuentan Vueltas en otras partes del circuito
![Tuning Graph](../img/Tuning%20Graph-03.svg)<br />
_Los cruces adicionales ocurren cuando *EnterAt* es demasiado bajo ._
* Elevar *EnterAt* hasta que *los cruces* solo comiencen cerca de la puerta del crono. (Use la página *Mariscal* después de guardar una carrera para determinar y guardar los mejores valores).

### Se registran varias vueltas a la vez
![Tuning Graph](../img/Tuning%20Graph-02.svg)<br />
Ocurren demasiadas vueltas cuando *ExitAt* está demasiado cerca de *EnterAt* porque las vueltas salen demasiado rápido.
* Elevar *EnterAt*, si es posible
* Bajar *ExitAt*

El ajuste *Tiempo mínimo de vuelta* siempre mantiene el primer cruce y descarta las vueltas posteriores que ocurren demasiado pronto. En este caso, esta configuración descartaría el primer cruce correcto y mantendría el segundo cruce incorrecto. Se recomienda dejar el comportamiento *Tiempo mínimo de vuelta* en *Resaltar* en lugar de *Descartar* para que un organizador de la carrera pueda revisar manualmente cada caso.

### Las Vueltas tardan mucho en registrarse
![Tuning Graph](../img/Tuning%20Graph-09.svg)<br />
_El registro de las vueltas tarda mucho tiempo en completarse si *ExiAt* es bajo. Esto no afecta la precisión del tiempo registrado.
* Elevar *ExitAt*

### El nodo nunca está *Cruzando*
![Tuning Graph](../img/Tuning%20Graph-07.svg)<br />
_No se registrarán vueltas si la señal RSSI nunca alcanza *EnterAt*._
* Bajar *EnterAt*

### El nodo nunca está *Despejado*
![Tuning Graph](../img/Tuning%20Graph-08.svg)<br />
_Las vueltas nunca se completarán si la señal RSSI nunca cae por debajo de *ExitAt*._
* Subir *ExitAt*
