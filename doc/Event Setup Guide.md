# Event Setup Guide

The basics of running an event are:
- Assign frequencies
- Add pilots
- Add heats and classes
- Run races

## Set Frequencies
Choose which set of requencies you will use for the event. From `Settings`, open `Frequency Setup`. Select a frequency for each seat and set unused seats to *Disabled*.

- Frequencies are

## Clear Existing Data (if needed)
From `Format`, open `Data Management`. Use the options here to reset or remove outdated information.

## Add Event Details (optional)
From `Format`, open the `Event` panel. Update the Event Name and Description.

- Event information is public and appears on the `Event` page.

## Add Pilots
From `Format`, open `Pilots` panel. Add an entry for each pilot participating. Give each pilot a *Callsign* to identify them.

- Callsigns are the primary pilot identifier and appear in most places
- Pilot names appear on the `Event` page and in heat selection boxes
- Phonetic changes how the timer text-to-speech engine announces a pilot; it is never shown visually

## Create Race Formats (optional)
From `Format`, open `Race Formats`. [Adjust the settings](User%20Guide.md#race-format) or create new formats to match your group's preferred settings.

## Add Heats and Classes
**Classes** are groups of heats, such as phases of the event, (like qualifying and finals,) or differing skill groups. When a race is saved, the results for the class will be calculated separately and grouped together as their own section within the race results. It is recommended to create a class for your pre-race practice sessions.

- If a race format is assigned to a class, it is enforced for all races within the class
- Classes will lock after a race has been saved

**Heats** are pilots flying together at exactly the same time. Create heats for each group of pilots. Select which pilots will fly together and add them to a heat slot. Seeded heats can be accomplished by changing the input type to "Heat" or "Class" and selecting the appropriate data source. Use "Auto Frequency" to have RotorHazard assign frequencies instead of making manual selections.

- Heats will lock after a race has been saved
- If pilot frequency assignments change after a race has run, create a new heat—do not modify a locked heat except to correct a mistake

## Run Race
Switch to the `Run` page. Find the appropriate heat in the dropdown. Use the "Start Race" button to begin a race. Race rounds are created automatically as races are run.

- Be sure to select the appropriate heat; "Practice mode" races are pilotless and cannot be saved

## Confirm
Save the race when it concludes. Use the `Marshal` page to [tune the timer](Tuning%20Parameters.md) for each pilot. Future races will self-calibrate using this data.

- Results become visible from the `Results` page.
