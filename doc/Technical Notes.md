# Technical Notes

The RotorHazard Race Timer is an open-source multi-node timing system that uses the video signals from FPV vehicles to determine when they cross the start/finish line.  The heart of the system is a Raspberry Pi, and each node has a dedicated Arduino Nano and RX5808 module.

The Raspberry Pi runs the Raspbian OS (with desktop), and the RotorHazard system uses a server component written in Python.  The stand-alone-server version uses the '[Flask](http://flask.pocoo.org)' library to serve up web pages to a computer or hand-held device, via a network connection.  An SQL database is used to store settings (via the '[flask_sqlalchemy](http://flask-sqlalchemy.pocoo.org)' extension), and the '[gevent](http://www.gevent.org)' library is used to handle asynchronous events and threading.  The web pages that are served up use the Javascript '[Articulate.js](http://articulate.purefreedom.com)' library to generate voice prompts.

The RotorHazard project is hosted on GitHub, here:  https://github.com/RotorHazard/RotorHazard