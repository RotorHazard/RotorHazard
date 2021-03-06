### RotorHazard S32_BPill Node Board Assembly

The recommended method for assembling an S32_BPill node is to mount the RX5808 module to the node board with
double-sided thermally-conductive tape
([HPFIX](https://www.amazon.com/Ceatech-Thermal-Double-sided-Adhesive-Computer/dp/B06ZY1JNJV?th%3D1) is
one example).

1 - Cut the thermal tape to the width of the RX5808 module.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image12.jpg)

2 - Apply the tape to the back of the RX5808 module without covering the solder
pads.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image9.jpg)

3 - On some RX5808 modules the audio-filter component (light blue) is not flush with the
PCB -- if that is the case then the tape should be cut away around the component so the RX5808 module
can lay flat on the node board.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image5.jpg)

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image7.jpg)

4 - Remove the backing from the tape and apply to the node board taking care to
align the solder pads of the RX5808 module with the pads on the node board.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image11.jpg)

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image8.jpg)

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image10.jpg)

5 - Solder all of the pads from the RX5808 module to the node board. (Some RX5808 modules have 3 extra pads that
do not correspond to pads on the node board -- these pads may be left unsoldered.)

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image6.jpg)

6 - Mount the right angle header pins putting the short side of the pins
through the 9 holes. Solder the pins straight using the one pin first
technique. If the pins are not parallel with the node board, warm the solder
and let it solidify while holding the pins straight.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image4.jpg)

7 - If [low profile sockets](https://github.com/RotorHazard/RotorHazard/blob/main/resources/S32_BPill_PCB/headers.md)
were installed on the main PCB to hold the modules, these 9 pins should be
trimmed to 3.5mm-4.0mm from the edge of the node board.

If you have access to the [3D printed pin trimming
jig](https://github.com/RotorHazard/RotorHazard/blob/main/resources/S32_BPill_PCB/trimjig.md),
slide the jig over the pins and clip to the edge of the jig.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image1.jpg)

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image2.jpg)

8 - After trimming the pins, the node module should slide into the low profile
socket with the bottom of the node board touching the sockets.

![](https://github.com/RotorHazard/rhfiles/raw/main/S32_BPill/nodeBuildPics/image3.jpg)
