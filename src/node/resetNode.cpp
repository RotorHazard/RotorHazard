#ifndef __TEST__
#include <Arduino.h>
#include "resetNode.h"

void initNodeResetPin()
{
  pinMode(NODE_RESET_PIN, INPUT_PULLUP);  // node reset for ISP
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
    pinMode(NODE_RESET_PIN, INPUT_PULLUP);
  } else {
    pinMode(NODE_RESET_PIN, OUTPUT);
    digitalWrite(NODE_RESET_PIN, LOW);
	}
}

#endif
