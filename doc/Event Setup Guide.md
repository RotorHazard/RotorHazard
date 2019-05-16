# Event Setup Guide

The basics of setting up an event are setting up pilots, heats, and nodes. You may also add event details and race classes if you desire.

## Clear Existing Data (if needed)
From Settings, open Database. Use the options here to remove outdated information from the database.

## Add Event Details (optional)
From Settings, open the Event panel. Update the Event Name and Description. These will show on the home page when users first visit the timer. Let pilots know what to expect during the event, such as the event format and schedule.

## Add Pilots
From Settings, open Pilots panel. Add an entry for each pilot participating. Pilot name will display on Event page; Callsign will be used for race results display and voice callouts. Test voice pronunciation with ">" button. If desired, write a phonetic spelling. This will never be displayed, but is used to pronounce the callsign.

## Create Race Formats (optional)
From Settings, open Race Formats. [Adjust the settings](User%20Guide.md#race-format) or create new formats to match your group's start staging type, win condition, etc.

## Add Heats and Classes
**Heats** are pilots flying together at exactly the same time. Name your heat, or leave the name empty to use a default name. Select which pilots will fly at exacly the same time and add them to a heat slot. The number of heat slots available is determined by the number of nodes connected to the timer. Use "None" for unused heat slots.

**Classes** are groups of pilots with shared characteristics. Create classes based on how your event is structured, if you need more than one class. Name your class for reference elsewhere. The class description is visible on the Event page. Setting an optional format forces all races within that class to use the selected Race Format settings.

Assign heats to classes in order to use them. When a race is saved for a heat with an assigned class, the results for the class will be calculated separately and appear as their own section within the race results.

## Tune Nodes to Environment
Once the timer is running at the race location, adjust the [node parameters and filtering settings](Tuning%20Parameters.md) to best match the desired type of racing. Optionally, create a profile for this location so you can easily load it again later.

## Example

8 pilots will gather for an indoor micro quad race. The event format is five qualifying rounds adding up the total lap count with the top four pilots advancing to a single final heat. Before the event, the organizer adds all of the pilots in the Pilots panel. Two classes are created, "Qualifying" and "Final", and both classes are assigned the "Whoop Sprint" race format. Two heats are created with four pilots each, and both heats are assigned to the "Qualifying" class. 

On the day of the event, the organizer selects the "Indoor" profile to set the desired frequencies and filtering settings and makes sure the nodes are tuned properly. From the Race page, the heats are run five times each. The timer organizes these races into rounds 1 through 5 for the results page as the races are run.

After the qualifying heats are over, the organizer checks the results page and reviews the "Qualifying" class to determine the top pilots. The organizer opens the Settings page and the Heats panel, creates a new heat and assigns the top four pilots into it, then assigns the "Final" class to the heat. The race for this final heat is run. On the results page, the "Final" class holds the results of the final and displays it separately from the others.
