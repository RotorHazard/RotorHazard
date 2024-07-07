# RotorHazard Hardware Build Resources

All supported build styles offer full timing accuracy but differ in size, cost, and ease of use.

<br />

## Full-featured S32_BPill

Standard, current build using the STM32 "Blue Pill" in place of individual Arduinos. Recommended for event managers with the available time and resources to acquire parts and complete the build.

- Supports up to 8 receivers (or more via USB)
- Supports all optional hardware features: current sensing, voltage sensing, RTC, buzzer, Status LED
- Ease-of-use features: power switch, shutdown button

### Full-size
[RotorHazard S32_BPill PCB](S32_BPill_PCB/)<br />
[RotorHazard S32_BPill Case](S32_BPill_case/)

### Compact (supports up to 6 receivers)
[RotorHazard 6 Node STM32](6_Node_BPill_PCB/)<br />
[RotorHazard 6 Node Case](6_node_BPill_case/)

<br />

## NuclearHazard Core

Designed for PCB manufacturer to be able to populate components instead of ordering individually. Available for purchase from the board designer.

- Supports up to 8 receivers (or more via USB)
- Supports buzzer
- Lowest cost self-contained build
- Smallest size
- Simplest assembly

[NuclearHazard Core (Prepopulated S32)](NuclearHazardCore/)

### NuclearHazard Atom

A compact, 2-node version of the NuclearHazard

[NuclearHazard Atom (2-node Prepopulated S32)](NuclearHazardAtom/)

<br />

## Arduino PCB

Uses the same basic hardware as the Delta 5, with improved features and ease of use.

- Supports up to 8 receivers when paired with second PCB (or more via USB)
- Highest cost for required components

[RotorHazard/Arduino PCB](PCB/)<br />
[3D Printed Enclosure for Arduino-based PCBs](enclosure/)

<br />

## Delta 5

Existing Delta 5 builds may be used but are not recommended for new builds.

- Supports up to 8 receivers when paired with second PCB (or more via USB)
- Highest cost for required components
- Arduinos must be manually addressed with code modification
- Arduinos must be removed to reprogram

Replace the Delta5 server software using the current RotorHazard server [setup instructions](doc/Software%20Setup.md), ensuring that you complete a [re-flash of the Arduinos](doc/Software%20Setup.md#rotorhazard-node-code).

<br />

## USB Node

Receivers may be connected to servers via USB insterface.

- Very low cost
- Does not contain server hardware; must connect to an existing server (for example, one of the above builds or installed directly onto a laptop)

[USB Nodes](../doc/USB%20Nodes.md)
