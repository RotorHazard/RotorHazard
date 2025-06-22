This firmware enables the beeper on the NuclearHazard boards. The only change is:

```
--- a/src/node/rhnode.cpp
+++ b/src/node/rhnode.cpp
@@ -645,7 +645,8 @@ void setBuzzerState(bool onFlag)
         {
             currentBuzzerStateFlag = true;
             pinMode(BUZZER_OUTPUT_PIN, OUTPUT);
-            digitalWrite(BUZZER_OUTPUT_PIN, BUZZER_OUT_ONSTATE);
+            //digitalWrite(BUZZER_OUTPUT_PIN, BUZZER_OUT_ONSTATE);
+            analogWrite(BUZZER_OUTPUT_PIN, 512);
```