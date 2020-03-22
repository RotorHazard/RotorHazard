#ifndef __TEST__
#include <Arduino.h>
#include "resetNode.h"

void initNodeResetPin()
{
	digitalWrite(NODE_RESET_PIN, HIGH);
}

void endSerial()
{
	Serial.end();
}

void resetPairedNode(int pinState)
{
	// Node reset for ISP
	// Resets other node wired to this node's reset pin (typically D12)
	if (pinState) {
		digitalWrite(NODE_RESET_PIN, HIGH);
	} else {
		digitalWrite(NODE_RESET_PIN, LOW);
	}
}

#endif
