#ifndef __TEST__
#include <Arduino.h>
#include "resetNode.h"

void initNodeResetPin()
{
	digitalWrite(NODE_RESET_PIN, HIGH);
}

void resetPairedNode()
{
	// Node reset for ISP
	// Resets other node wired to this node's reset pin (typically D12)
	digitalWrite(NODE_RESET_PIN, HIGH);
	delay(50);
	digitalWrite(NODE_RESET_PIN, LOW);
	delay(100);
	digitalWrite(NODE_RESET_PIN, HIGH);
}
#endif
