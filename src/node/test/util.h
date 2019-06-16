#define N_2 (SmoothingSamples/2+1)
#define milliTick(nano) (nano->micros += 1000)
#define timestamp(sendCount) ((sendCount)*N_2-SmoothingTimestampSize)

void sendSignal(GodmodeState* nano, int rssi) {
  for(int t=0; t<N_2; t++) {
    rssiProcess(rssi, millis());
    milliTick(nano);
  }
}
