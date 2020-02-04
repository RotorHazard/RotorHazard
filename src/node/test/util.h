#define N_2 (SmoothingSamples/2+1)
#define milliTick(nano) (nano->micros += 1000)
#define timestamp(sendCount) ((sendCount)*N_2-SmoothingTimestampSize)
#define time(sendCount) ((sendCount)*N_2)
#define readPeak() (history.peakSend.rssi = 0)
#define readNadir() (history.nadirSend.rssi = MAX_RSSI)

void sendSignal(GodmodeState* nano, int rssi) {
  for(int t=0; t<N_2; t++) {
    rssiProcess(rssi, millis());
    milliTick(nano);
  }
}
