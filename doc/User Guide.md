# Delta 5 Race Timer User Guide

### Hardware and Software Setup
1. Follow the instructions here if not done already: [/doc/Hardware and Software Setup Instructions.md](Hardware%20and%20Software%20Setup%20Instructions.md)

### Database Setup and Configure
1. Open a browser and type in the ip address of the timing system on your network.

2. Go to the 'Database' page.

3. Click the 'Create Database' button at the bottom, this adds all the tables in the 'vtx' database.

4. Enter the number of nodes installed in the system and then click 'Initialize System'.

### Set Triggers

1. Go to the 'Settings' page.

2. Click 'Start System' to start polling data from the nodes.

3. Power a drone and place it 10 feet from the timer.

4. Note that the rssi value for the node on that frequency has increased.

5. Click the 'Set' button for that node to save the current 'rssi' reading as the trigger value.

6. Move the drone to within 5 feet of the timer.

7. Ensure that the current 'rssi' reading from the node is at least 15 points more than the tigger value.

8. The trigger function works by looking for a value 10 points more than the trigger value and then counts a lap when the rssi falls below 10 points less than the trigger value.

9. Repeat this process for each channel/drone.

### Running Races

1. With 'System Status' as 'Running' on the settings page, go to the 'Race' page.

2. Move all drones 10 plus feet away from the timing system, the rssi values must be 10 points less than the trigger value.

3. Click 'Start Race'

4. Give the nodes 5 seconds to initialize and then tell the pilots to start racing.

5. The first pass through the gate won't show anything but when a pilot comes through the gate a second time it will register that as the first lap.

6. When the race is completed click 'Stop Race'

7. Click 'Save Laps' to store the results of a good race.

8. Click 'Clear Laps' and then go back to step 2 to run another race.
