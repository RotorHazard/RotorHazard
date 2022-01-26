import csv
import sys
import matplotlib.pyplot as plt

pins = {}
with open(sys.argv[1]) as f:
    reader = csv.reader(f)
    header = next(reader)
    for i, r in enumerate(reader):
        t = int(r[0])
        pin = int(r[1])
        v = int(r[2])
        if pin >= 18: # SPI pins
            if pin in pins:
                pin_data = pins[pin]
            else:
                pin_data = ([], [])
                pins[pin] = pin_data
            pin_data[0].append(i)
            pin_data[1].append(v)
        # continually current state of other pins
        if i > 0:
            for other, pin_data in pins.items():
                if other != pin:
                    pin_data[0].append(i)
                    pin_data[1].append(pin_data[1][-1])

for pin, pin_data in pins.items():
    plt.plot(pin_data[0], pin_data[1], label=str(pin))
plt.legend(loc='upper right')
plt.show()
