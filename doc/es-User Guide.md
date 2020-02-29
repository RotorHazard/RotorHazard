# RotorHazard Race Timer - Guía de Usuario

## Configuración Inicial

### Configuración de HARDWARE y SOFTWARE
Siga las siguientes instrucciones si aún no lo ha hecho:
[doc/Hardware Setup.md](Hardware%20Setup.md)
[doc/Software Setup.md](Software%20Setup.md)

### Configurar archivo de configuración
En el directorio "src/server", busque *config-dist.json* y cópielo en *config.json*. Edite este archivo y modifique los valores HTTP_PORT, ADMIN_USERNAME y ADMIN_PASSWORD. Python requiere estrictamente que este archivo sea JSON válido. Una utilidad linter como [JSONLint](https://jsonlint.com/) puede ayudarle a revisar errores de síntesis.

HTTP_PORT es el valor del puerto en el que se ejecutará el servidor. De manera predeterminada, HTTP usa el puerto 80. Otros valores requerirán que el puerto se incluya como parte de la URL ingresada en los navegadores del cliente. Si otros servicios web se están ejecutando en la Pi, el puerto 80 puede estar en uso y el servidor no podrá iniciarse. Si se usa el puerto 80, el servidor puede necesitar ejecutarse usando el comando *sudo*. El puerto 5000 debería estar disponible. Algunas versiones de LiveTime solo se conectarán a un servidor en el puerto 5000.

ADMIN_USERNAME y ADMIN_PASSWORD son las credenciales de inicio de sesión que se necesitarán para realizar cambios en el apartado de configuración.


### Conectarse al servidor
Se puede usar una computadora, teléfono o tableta para interactuar con el crono iniciando un navegador web e ingresando la dirección IP de Raspberry Pi. La Raspberry Pi puede conectarse mediante un cable de ethernet o una red WiFi disponible. Si no se conoce la dirección IP de Pi, se puede ver con el comando de terminal "ifconfig" y se puede configurar con un valor estático en el escritorio de Pi a través de "Preferencias de red". Si el Pi está conectado a una red WiFi, su dirección IP se puede encontrar en la lista 'Clientes' en la página de administración del enrutador de la red.

En el navegador web, escriba la dirección IP del crono y el valor del puerto que configuró en el archivo de config.json (o deje el puerto: si está configurado en 80).

```
XXX.XXX.XXX.XXX:5000
```

Una vez que la página se muestre con éxito, se puede marcar en el navegador. Las páginas reservadas para el director de carrera ("Admin/Configuración") están protegidas con contraseña con el nombre de usuario y la contraseña especificados en el archivo de config.json

## Pages

### Home

Esta página muestra el nombre y la descripción del evento, junto con un conjunto de botones para otras páginas.


### Evento

Esta es una página pública que muestra la configuración de clase actual (si corresponde) y un resumen de los pilotos y sus series con asignación de canales.


### Resultados

Esta página pública mostrará resultados y estadísticas calculadas de todas las carreras guardadas anteriormente, organizadas en paneles desplegables. Los resultados agregados se muestran para cada serie con múltiples rondas, cada clase y el evento completo.

### Espectador

Esta página muestra información sobre la carrera actual, incluido el tiempo de carrera en tiempo real, los tiempos de vuelta de los pilotos y la tabla de clasificación. Se actualiza automáticamente con el evento y es adecuado para proyectar en una pantalla de visualización destacada.

En la sección Control de audio, el usuario puede seleccionar si se anuncia por voz a un piloto, todos los pilotos o ningún piloto. De esta manera, un piloto podría elegir escuchar solo sus propias vueltas anunciadas. El usuario también puede ajustar la voz, el volumen, la velocidad y el tono de estos anuncios.


### Configuración

Esta página permite cambiar la configuración opcional del crono y la configuración de eventos.

#### Configuración de frecuencias
Elija un preajuste o seleccione manualmente las frecuencias para cada nodo. La selección de frecuencias arbitrarias es posible, igual que deshabilitar un nodo. Actualmente se calcula y se muestra en la parte inferior del panel la puntuación IMD para las frecuencias seleccionadas. 

Los perfiles contienen frecuencias y valores de ajuste de nodos. Cambiar esta lista activa inmediatamente el perfil seleccionado, y cambiar las frecuencias actuales y la sintonización de nodos se guarda inmediatamente en el perfil.

#### Ajuste del sensor
Vea [doc/Tuning Parameters.md](Tuning%20Parameters.md) para una descripción detallada sobre la sintonización y calibrado de los nodos.

#### Evento y Clases
La información del evento se muestra en la página de inicio cuando los usuarios se conectan por primera vez al sistema.

No se requieren clases para eventos; no es necesario crear una clase a menos que tenga dos o más en el evento. Las clases se pueden usar para tener estadísticas generadas por separado para grupos de series. Por ejemplo, clasificatorias Open y Spec, o clasificatorias Principiante/Pro.

#### Series
Agregue series hasta que haya suficientes para todas las carreras y pilotos. Se pueden agregar nombres de serie opcionales si se desea. Las ranuras dentro de la serie se pueden establecer en *Ninguno* si no se asigna ningún piloto allí.

Si está usando clases, asigne cada serie a una clase. Asegúrese de agregar suficientes series para cada piloto en cada clase; las series asignadas a una clase no están disponibles en otra.

A medida que lance carreras, las clases (clasificatorias) se bloquearán y no podrán modificarse. Esto protege los datos de carrera guardados para que sean válidos. Para modificar las series nuevamente, abra el panel *Base de datos* y borre las carreras.

#### Pilotos
Agregue una entrada para cada piloto que competirá. El sistema anunciará pilotos en función de su indicativo "callsing". Se puede usar una ortografía fonética para un "callsing" para influir en cómo se oirá el nombre; aunque es opcional.

#### Control de audio
Todos los controles de audio son locales para el navegador y el dispositivo donde los configuró, incluida la lista de idiomas, volúmenes disponibles y qué anuncios o indicadores están en uso.
La selección de voz elige el motor de texto a voz. Las selecciones disponibles serán proporcionadas por el navegador web y el sistema operativo.

Los anuncios permiten al usuario elegir escuchar el indicativo, el número de vuelta y/o el tiempo de vuelta de cada piloto al cruzar. El anuncio del "Tiempo de carrera" indicará periódicamente cuánto tiempo ha transcurrido o queda, según el modo de temporizador en el formato de carrera. "Tiempo de Vuelta de Equipo" se usa solo cuando el "Modo de Carrera por Equipos" está habilitado.

El volumen de voz, la velocidad y el tono controlan todos los anuncios de texto a voz. "Volumen de tono" controla las señales de inicio y finalización de la carrera.

Los pitidos de los indicadores son tonos muy cortos que proporcionan información sobre cómo funciona el temporizador, y son más útiles cuando se trata de sintonizarlo. Cada nodo se identifica con un tono de audio único. "Cruce entrado" emitirá un pitido cuando comience un pase y "Cruce salido" emitirá dos pitidos rápidamente cuando se complete un pase. El "Botón de vuelta manual" emitirá un pitido si se usa el botón "Manual" para forzar un pase simulado.

#### Formato de carrera
Los formatos de carrera recopilan configuraciones que definen cómo se lleva a cabo una carrera. Elige un formato de carrera activo. La configuración que ajuste aquí se guardará en el formato actualmente activo.

El modo de temporizador puede contar hacia arriba o hacia atrás. Use "Cuenta Ascendente" para un estilo heads-up, "primero en X vueltas". Use "Cuenta Atrás" para un formato de tiempo fijo. La duración del temporizador solo se usa en el modo "Count Down".

El modo de temporizador de etapas afecta si la visualización del tiempo será visible antes de una carrera. "Mostrar cuenta regresiva" mostrará el tiempo hasta la señal de inicio de la carrera; "Ocultar cuenta regresiva" mostrará "Listo" hasta que comience la carrera.

El Retardo de inicio mínimo y máximo ajusta cuántos segundos dura el cronómetro de etapas (antes de la carrera). Ajústelos al mismo número durante un tiempo de contado fijo, o a números diferentes para un tiempo aleatorio dentro de este rango.

El tiempo mínimo de vuelta y el modo de carrera en equipo no se almacenan con el formato de carrera.

El tiempo mínimo de vuelta descarta automáticamente los pases que hubieran registrado vueltas menores a la duración especificada. Úselo con precaución, ya que esto podría descartar datos que podrían haber sido válidos.

#### Efectos LED
Elija un efecto visual para cada evento del temporizador. El temporizador mostrará este efecto cuando ocurra el evento, anulando inmediatamente cualquier visualización o efecto existente. Algunos efectos visuales solo están disponibles en eventos de temporizador particulares. El evento modifica algunos efectos visuales, en particular el color del cruce de la puerta que entra/sale. La mayoría de los efectos se pueden previsualizar a través del panel de control LED.

Algunos efectos de LED pueden retrasarse un poco si el temporizador está ocupado con tareas críticas. (Otros, como el inicio de la carrera, nunca se retrasan). Debido a este efecto y los cruces potencialmente concurrentes, _"Desactivar"_ generalmente debe evitarse para las salidas de la puerta. En su lugar, use _"Sin cambio"_ en la entrada de la puerta y el efecto deseado en la salida de la puerta.

_Esta sección no aparecerá si su crono no tiene LED configurados. Aparece un aviso en el registro de inicio._

#### Control LED
Esta sección anulará la pantalla LED actual. Elija apagar temporalmente la pantalla, mostrar algunos colores preconfigurados, mostrar cualquier color personalizado o mostrar un efecto definido. También puede usar el control deslizante para ajustar el brillo de su panel. La configuración ideal para cámaras FPV es donde el panel iluminado coincide con el brillo de un objeto blanco. Esto coloca la salida del panel dentro del rango dinámico de lo que la cámara puede capturar. Sin embargo, el uso de un ajuste de brillo bajo distorsiona la reproducción del color y la suavidad de las transiciones de color.

_Esta sección no aparecerá si su temporizador no tiene LED configurados. Aparece un aviso en el registro de inicio._

#### Base de datos
Elija hacer una copia de seguridad de la base de datos actual (guardar en un archivo en el pi y solicitar que se descargue) o borrar datos. Puede borrar carreras, clases, series y pilotos.

#### Sistema
Elija el idioma de la interfaz y cambie los parámetros que afectan la apariencia del temporizador, como su nombre y combinación de colores. También puede apagar i reiniciar el servidor desde aquí.


### Carrera

Esta página te permite controlar el crono y correr carreras.

Seleccione la Serie para la carrera que se ejecutará a continuación.

Comienza la carrera cuando estés listo. (Hotkey: <kbd>z</kbd>) El temporizador hará una comunicación rápida con el servidor para compensar el tiempo de respuesta del cliente / servidor, luego comenzará el procedimiento de clasificación definido por el formato de carrera actual.

Los parámetros de ajuste se pueden ajustar aquí mediante el botón "⚠". Ver [doc/Tuning Parameters.md](Tuning%20Parameters.md) para una descripción detallada y guía de ajuste.

Durante la carrera, hay una "×" al lado de cada vuelta contada. Esto descartará ese pase de vuelta, por lo que su tiempo se moverá a la siguiente vuelta. Use esto para eliminar pases extra erróneas, o limpiar a los pilotos que vuelan cerca de la puerta de inicio después de que termine su carrera.

Se proporciona un botón "+ Vuelta" para forzar el paso de vuelta para que ese nodo se registre inmediatamente.

Cuando termine una carrera, use el botón "Detener carrera" (Hotkey: <kbd>x</kbd>) para dejar de contar vueltas. Debe hacerlo incluso si el temporizador llega a cero en un formato de "Cuenta atrás"; un formato de carrera popular permite a los pilotos terminar la vuelta en la que se encuentran cuando expira el tiempo. Para obtener los mejores resultados, despeje la puerta de sincronización y permita que finalicen todos los cruces válidos antes de detener la carrera.

Una vez que finaliza una carrera, debes elegir "Guardar vueltas" o "Borrar vueltas" antes de comenzar otra carrera. "Guardar vueltas" (Hotkey: <kbd>c</kbd>) almacenará los resultados de la carrera en la base de datos y los mostrará en la página "Resultados". "Descartar Vueltas" (Hotkey: <kbd>v</kbd>) descartará los resultados de la carrera. Guardar vueltas avanzará automáticamente la selección de la serie a la siguiente con la misma clase que la carrera guardada.

El panel Gestión de Carrera proporciona acceso rápido para cambiar el formato de carrera actual, el perfil, el tiempo mínimo de vuelta o el modo Team Racing. _Audio Control_ y _LED Control_ son igules que en la página Configuración. La Exportación del Historial crea un archivo CSV para descargar los valores RSSI registrados en la carrera completada más recientemente. "Tiempo hasta el inicio de la carrera" programará una carrera que se ejecutará en un momento futuro. Los operadores pueden usar esto para establecer un límite estricto en la cantidad de tiempo permitido para que los pilotos se preparen, o para iniciar el crono y luego participar en la carrera ellos mismos.

### Mariscal

Ajusta los resultados de las carreras guardadas.

Seleccione la serie, la ronda y el piloto a ajustar. Los puntos de entrada y salida se cargan automáticamente a partir de los datos de carrera guardados. Ajuste los puntos de entrada y salida para recalibrar la carrera. "Cargar desde el nodo" para cargar los datos guardados actualmente en el nodo y que se muestren en el gráfico. "Guardar en nodo" para copiar los valores ajustados en el gráfico al nodo. "Recalcular carrera" para usar los valores activos de entrada/salida como puntos de calibrado para una "repetición" de la carrera. Esto borrará las vueltas actuales y las reemplazará con la información recalculada. Las vueltas introducidas manualmente se conservarán.

Agregue vueltas ingresando el tiempo de cruce en segundos desde el comienzo de la carrera, luego presione el botón "Agregar vuelta".

Elimine las vueltas con el botón "×" en la vuelta no deseada. Las vueltas eliminadas se eliminan de los cálculos, pero permanecen presentes en los datos para referencia posterior. "Borrar vueltas" para eliminar permanentemente los datos de la base de datos.

Puede hacer clic/tocar el gráfico para establecer los puntos de entrada/salida, activar el recálculo y resaltar vueltas específicas. Al hacer clic en las vueltas de la lista también se resalta el gráfico. Presione <kbd>borrar</kbd> o <kbd>x</kbd> para borrar una vuelta resaltada. Las vueltas activas se muestran en verde, y las vueltas eliminadas cambian a rojo. El ancho del indicador de vuelta muestra los puntos de entrada/salida, y el resaltado amarillo dibuja una línea en el tiempo exacto de vuelta dentro de esa ventana.

"Realizar Cambios" cuando haya terminado de ajustar los datos de la carrera para guardarlos en la base de datos y actualizar los resultados de la carrera.
