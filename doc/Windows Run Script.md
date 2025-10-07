# Windows Run Script

Use this guide if you want to run a RotorHazard server on Windows without needing to have physical timer hardware.  

Why might you want to do this?
1. You are new to RotorHazard or want to experiment with it without needing hardware
2. You use a plugin that doesn’t need physical hardware such as the Velocidrone Controls
3. You want to develop plugins and want a way to run the server

## Setup
1. Install [Python](https://www.python.org) on your PC if you don't have it already. You can do this by going to the [Microsoft Store](https://apps.microsoft.com/search?query=python) and installing the latest version. At the time of writing this is 3.13 but it gets updated every year.
2. From the RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), download the "Source code (zip)" file.
3. Unzip the downloaded file into a directory (aka folder) on the computer.
4. Navigate to the `RotorHazard\tools` folder and run the `rh_win_run.bat` script.
5. The script will create a virtual environment (if needed) and install the required packages into that virtual environment, and then run the server. When the server is running you should see "Running http server at port 5000" in the terminal.
6. Open a web browser and navigate to [http://localhost:5000](http://localhost:5000)

You will now be able to use RotorHazard as you would normally, but with simulated (mock) timing nodes.

## Notes

If the terminal says something like "ModuleNotFoundError: No module named..." then delete the Python 'venv' folder and re-run the script.

If the installation of required packages fails with a message like "error: Microsoft Visual C++ 14.0 is required", the "Desktop development with C++" Tools may be downloaded (from [here](https://aka.ms/vs/17/release/vs_BuildTools.exe)) and installed to satisfy the requirement.

<br/>

-----------------------------

See Also:  
[doc/Software Setup.md#other-operating-systems](Software%20Setup.md#other-operating-systems)  
