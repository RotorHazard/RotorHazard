#include <ArduinoUnitTests.h>
#include "../util/lowpass15hz-filter.h"
#include "../util/lowpass20hz-filter.h"
#include "../util/lowpass50hz-filter.h"
#include "../util/lowpass100hz-filter.h"
#include "../util/median-filter.h"
#include "../util/composite-filter.h"

#define PI 3.1415926535897932384626433832795
#define HALF_PI 1.5707963267948966192313216916398
#define TWO_PI 6.283185307179586476925286766559

#define N 2000 // 2 sec test signal duration
#define ONE_SEC 1000 // skip the first second of the output to allow it to settle

#define toSecs(t) (t/1000.0)

int filter(char name[], Filter<rssi_t>& lpf, double testFreq, rssi_t output[]) {
    int offset = -1;
    FILE *fp = fopen(name, "wt");
    if (!fp) {
        printf("Cannot write to %s\n", name);
    }
    fprintf(fp, "t, in, out\n");
    for(int t=0; t<N; t++) {
        rssi_t x = MAX_RSSI/2.0*(1.0+sin(TWO_PI*testFreq*toSecs(t)-HALF_PI));
        lpf.addRawValue(t, x);
        if (lpf.isFilled()) {
            if (offset == -1) {
                offset = t;
            }
            rssi_t xf = lpf.getFilteredValue();
            output[t] = xf;
            fprintf(fp, "%d, %d, %d\n", t, x, xf);
        }
    }
    fclose(fp);
    return offset;
}

#define assertMaxMin(output, offset, freq) \
{ \
    int t_max = ONE_SEC + offset + (int)(1000.0/2.0/freq); \
    int t_zero = ONE_SEC + offset + (int)(1000.0/freq); \
    rssi_t max = output[t_max]; \
    rssi_t zero = output[t_zero]; \
    rssi_t expectedMax = 0; \
    rssi_t expectedMin = MAX_RSSI; \
    for (int i=ONE_SEC + offset; i<N; i++) { \
        expectedMax = max(output[i], expectedMax); \
        expectedMin = min(output[i], expectedMin); \
    } \
    assertEqual((int)expectedMax, (int)max); \
    assertEqual((int)expectedMin, (int)zero); \
}

unittest(lpf15_with_8hz_signal)
{
  LowPassFilter15Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 8;
  rssi_t output[N];
  int offset = filter("lpf15_with_8hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(lpf20_with_2hz_signal)
{
  LowPassFilter20Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 2;
  rssi_t output[N];
  int offset = filter("lpf20_with_2hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(lpf20_with_8hz_signal)
{
  LowPassFilter20Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 8;
  rssi_t output[N];
  int offset = filter("lpf20_with_8hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(lpf50_with_5hz_signal)
{
  LowPassFilter50Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 5;
  rssi_t output[N];
  int offset = filter("lpf50_with_5hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(lpf50_with_25hz_signal)
{
  LowPassFilter50Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 25;
  rssi_t output[N];
  int offset = filter("lpf50_with_25hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(lpf100_with_10hz_signal)
{
  LowPassFilter100Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 10;
  rssi_t output[N];
  int offset = filter("lpf100_with_10hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(lpf100_with_100hz_signal)
{
  LowPassFilter100Hz lpf;
  assertFalse(lpf.isFilled());
  double freq = 100;
  rssi_t output[N];
  int offset = filter("lpf100_with_100hz_signal.csv", lpf, freq, output);
  assertMaxMin(output, offset, freq);
}

unittest(composite_with_10hz_signal)
{
  LowPassFilter50Hz lpf50;
  MedianFilter<rssi_t, 7, 0> mf;
  CompositeFilter<rssi_t> lpf(lpf50, mf);
  assertFalse(lpf.isFilled());
  double freq = 20;
  rssi_t output[N];
  int offset = filter("composite_with_10hz_signal.csv", lpf, freq, output);

  int t_max = ONE_SEC + offset + (int)(1000.0/2.0/freq);
  int t_zero = ONE_SEC + offset + (int)(1000.0/freq);
  rssi_t max = output[t_max];
  rssi_t zero = output[t_zero];
  rssi_t expectedMax = 0;
  rssi_t expectedMin = MAX_RSSI;
  for (int i=ONE_SEC + offset; i<N; i++) {
      expectedMax = max(output[i], expectedMax);
      expectedMin = min(output[i], expectedMin);
  }
  assertMore((int)expectedMax, (int)max);
  assertLess((int)expectedMin, (int)zero);
}

unittest_main()
