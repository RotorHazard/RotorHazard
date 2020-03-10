# Desarrollo

Este documento es principalmente para desarrolladores.
Si planea contribuir a RotorHazard abriendo una solicitud de extracción para una corrección de errores o función, lea el siguiente texto antes de comenzar. Esto le ayudará a enviar su contribución en un formulario que tenga buenas posibilidades de ser aceptado.

## Usando git y GitHub

Asegúrese de comprender el flujo de trabajo de GitHub: https://guides.github.com/introduction/flow/index.html

Mantenga las solicitudes de extracción enfocadas solo en una cosa, ya que esto hace que sea más fácil combinar y probar de manera oportuna.

Si necesita ayuda con las solicitudes de extracción, hay guías en GitHub aquí:

https://help.github.com/articles/creating-a-pull-request

El flujo principal para un contribuidor es el siguiente:

1. Inicie sesion en GitHub, vaya a [RotorHazard repository](https://github.com/RotorHazard/RotorHazard) y presione `fork`;
2. Luego use el comando line/terminal en su ordenador: `git clone <url to YOUR fork>`;
3. `cd RotorHazard`;
4. `git checkout master`;
5. `git checkout -b my-new-code`;
6. Realizar cambios;
7. `git add <files that have changed>`;
8. `git commit`;
9. `git push origin my-new-code`;
10. Cree una solicitud de extracción con la interfaz de usuario de GitHub para combinar los cambios de su nueva sucursal en `RotorHazard/master`;
11. Repita desde el paso 4 para otros cambios nuevos.

Lo principal a recordar es que se deben crear solicitudes de extracción separadas para ramas separadas. Nunca cree una solicitud de extracción desde su rama `master`.

Una vez que haya creado el PR, cada nuevo commit / push en su rama se propagará desde su bifurcación al PR en el repositorio principal de GitHub / RotorHazard. Echa un vistazo a otra rama primero si quieres algo más.

Más tarde, puede obtener los cambios del repositorio RotorHazard en su rama `master` agregando RotorHazard como un control remoto git y fusionándose de la siguiente manera:

1. `git remote add RotorHazard https://github.com/RotorHazard/RotorHazard.git`
2. `git checkout master`
3. `git fetch RotorHazard`
4. `git merge RotorHazard/master`
5. `git push origin master` es un paso opcional que actualizará su fork en Github.

Si usa Windows, [TortoiseGit](https://tortoisegit.org) es altamente recomendable.

## Estilo de codificación 

Cuando se agrega código a un archivo existente, el nuevo código debe seguir lo que ya existe en términos de sangría (espacios frente a pestañas), llaves, convenciones de nomenclatura, etc.

Si un RP está modificando la funcionalidad, intente evitar cambios innecesarios en los espacios en blanco (es decir, agregar / eliminar espacios finales o líneas nuevas), ya que esto hace que sea más difícil ver los cambios funcionales. Las mejoras en el espacio en blanco y el estilo de código deben implementarse RP que solo hagan esas cosas.

## Proyecto Eclipse PyDev

El [Eclipse IDE](https://www.eclipse.org/eclipseide/) (with the [PyDev](https://www.pydev.org) extension) puede usarse para editar el código fuente de Python: los archivos ".project" y ".pydevproject" definen el proyecto, que puede cargarse a través de "Archivo | Abrir proyectos desde el sistema de archivos ..." en Eclipse.
