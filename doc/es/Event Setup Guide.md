# Gía de configuración de Evento

Los conceptos básicos de la configuración de un evento son la configuración de pilotos, series y nodos. También puede agregar detalles del evento y clases de carrera si lo desea.

## Borrar datos existentes (si fuese necesario)
Desde Configuración, abrir Base de datos. Usar entre las opciones disponibles para borrar los datos que sean obsoletos.

## Añadir Detalles al Evento (opcional)
Desde Configuración, abra el panel Evento. Actualice el nombre y la descripción del evento. Estos se mostrarán en la página de inicio cuando los usuarios visiten el RotorHazard por primera vez. Aquí puede informar a los pilotos qué pueden esperar del evento, como cuál será el formato o el horario.

## Añadir Pilotos
Desde Configuración, abra el panel Pilotos. Agregue una entrada para cada piloto que participe. El nombre del piloto se mostrará en la página del evento; Callsign (alias) se usará para mostrar los resultados de la carrera y las llamadas de voz. Prueba la pronunciación de la voz con el botón ">". Si lo desea, escriba una ortografía fonética para los nombres que no suenen igual. Esto nunca se mostrará, pero se usa para pronunciar el nombre.

## Crear Formatos de Carrera (opcional)
Desde Configuración, abrir Formato de Carreras. [Adjust the settings](User%20Guide.md#race-format) o crear nuevos formatos para que coincidan con el tipo de puesta en escena de inicio de su grupo, la condición de victoria, etc.

## Añadir Series y Clases
**Series** son pilotos que vuelan juntos exactamente al mismo tiempo. Asigne un nombre a su serie o deje el nombre vacío para usar un nombre predeterminado. Seleccione qué pilotos volarán exactamente al mismo tiempo y agréguelos a una casilla de la serie. El número de casillas de serie disponibles está determinado por el número de nodos conectados al temporizador. Use "Ninguno" para las casillas de la serie no utilizadas.

**Clases** son grupos de pilotos con características compartidas. Cree clases basadas en cómo está estructurado su evento, si necesita más de una clase. Nombre su clase para referencia en otro lugar. La descripción de la clase es visible en la página del evento. Establecer un formato opcional obliga a todas las carreras dentro de esa clase a usar la configuración de Formato de Carrera seleccionado.

Asigne series a las clases para usarlos. Cuando una carrera se guarda para una serie con una clase asignada, los resultados de la clase se calcularán por separado y aparecerán como su propia sección en los resultados de la carrera.

## Sintonizar los Nodos al Entorno
Una vez que el temporizador esté funcionando en el lugar de la carrera, ajuste el [node parameters and filtering settings](Tuning%20Parameters.md) para que coincida mejor con el tipo de carrera deseado. Opcionalmente, cree un perfil para esta ubicación para que pueda cargarlo fácilmente más tarde.

## Ejemplo
8 pilotos se reunirán para una carrera de micro quad en interiores. El formato del evento es de cinco rondas clasificatorias que suman el recuento total de vueltas con los cuatro mejores pilotos avanzando a una única serie final. Antes del evento, el organizador agrega todos los pilotos en el panel Pilotos. Se crean dos clases, "Calificación" y "Final", y a ambas clases se les asigna el formato de carrera "Whoop Sprint". Se crean dos series con cuatro pilotos cada una, y ambas series se asignan a la clase "Calificación".

El día del evento, el organizador selecciona el perfil "Interior" para establecer las frecuencias deseadas y la configuración de filtrado y se asegura de que los nodos estén sintonizados correctamente. Desde la página Carrera, las eliminatorias se ejecutan cinco veces cada una. El temporizador organiza estas carreras en rondas 1 a 5 para la página de resultados a medida que se ejecutan las carreras.

Una vez que terminan las eliminatorias clasificatorias, el organizador revisa la página de resultados y revisa la clase "Calificación" para determinar los mejores pilotos. El organizador abre la página Configuración y el panel Calienta, crea un nuevo calor y asigna los cuatro mejores pilotos en él, luego asigna la clase "Final" al calor. La carrera por este último calor se corre. En la página de resultados, la clase "Final" contiene los resultados de la final y los muestra por separado de los demás.
