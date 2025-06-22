# Notas técnicas

RotorHazard Race Timer es un sistema de temporización de múltiples nodos de código abierto que utiliza las señales de video de los drones FPV para determinar cuándo cruzan la línea de inicio / finalización. El corazón del sistema es una Raspberry Pi, y cada nodo está compuesto de un Arduino Nano y un RX5808.

El Raspberry Pi ejecuta el sistema operativo Raspbian (con escritorio), y el sistema RotorHazard utiliza un componente de servidor escrito en Python. La versión de servidor independiente utiliza el'[Flask](http://flask.pocoo.org)'biblioteca para servir páginas web a un ordenador o dispositivo portátil, a través de una conexión de red. Se utiliza una base de datos SQL para almacenar configuraciones (a través de'[SQLAlchemy](https://www.sqlalchemy.org)' extensión), y la '[gevent](http://www.gevent.org)'biblioteca se utiliza para manejar eventos asincrónicos y subprocesos. Las páginas web que se sirven utilizan el Javascript '[Articulate.js](http://articulate.purefreedom.com)' biblioteca para generar mensajes de voz.

El proyecto RotorHazard está alojado en GitHub, aquí: https://github.com/RotorHazard/RotorHazard