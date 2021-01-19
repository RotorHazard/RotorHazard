#include "filter.h"
#define CIRCULAR_BUFFER_INT_SAFE
#include "CircularBuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=20&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.02
//constant delay in the pass-band (variably less above)
class LowPassFilter20Hz : public Filter<rssi_t>
{
    private:
        float v[3];
        rssi_t nextValue;
        CircularBuffer<mtime_t,12> timestamps; // delay correct for pass-band
    public:
        LowPassFilter20Hz()
        {
            v[0] = 0.0;
            v[1] = 0.0;
        }

        bool isFilled() {
            return timestamps.isFull();
        }

        void addRawValue(mtime_t ts, rssi_t x)
        {
            v[0] = v[1];
            v[1] = v[2];
            v[2] = (5.593440209108096160e-3 * x)
                 + (-0.75788377219702429688 * v[0])
                 + (1.73551001136059190877 * v[1]);
            nextValue = (rssi_t)((v[0] + v[2]) + 2 * v[1]);

            timestamps.push(ts);
        }

        rssi_t getFilteredValue() {
            return nextValue;
        }

        mtime_t getFilterTimestamp() {
            return timestamps.first();
        }
};
