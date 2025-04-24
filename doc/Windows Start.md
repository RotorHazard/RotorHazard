## Introduction
Use this guide if you want to run a RotorHazard server on windows without needing to have physical timer hardware.  
Why might you want to do this?
1. You are new to RotorHazard or want to experiment with it without needing hardware
2. You use a plugin that doesn’t need physical hardware such as the Velocidrone Controls
3. You want to develop plugins and want a way to run the server

## Setup
1. Install python on your PC if you don't have it already. You can do this by going to the [Microsoft Store](https://apps.microsoft.com/search?query=python) and installing the latest version. At the time of writing this is 3.13 but it gets updated every year.
2. Download a copy of RotorHazard from the [release page](https://github.com/RotorHazard/RotorHazard/releases) and save it somewhere useful.
3. Unzip the RotorHazard file you just downloaded
4. Navigate to the RotorHazard\src\server folder and run the windows_rh_start.bat script
5. The script will create a virtual environment and install the required packages into that virtual environment and then run the server. When the server is running you should see "Running http server at port 5000" in the terminal
6. Open a web browser and navigate to [http://localhost:5000](http://localhost:5000)

You will now be able to use RotorHazard as you would normally using mock timing nodes

If the terminal says something like "ModuleNotFoundError: No module named" delete the RotorHazard\src\server\venv folder and re-run this script
