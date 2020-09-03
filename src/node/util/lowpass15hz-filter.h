#include "filter.h"
#define CIRCULAR_BUFFER_INT_SAFE
#include "CircularBuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=15&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.015
//constant delay in the pass-band (variably less above)
class LowPassFilter15Hz : public Filter<rssi_t>
{
    private:
        float v[3];
        rssi_t nextValue;
        CircularBuffer<mtime_t,16> timestamps; // delay correct for pass-band
    public:
        LowPassFilter15Hz()
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
            v[2] = (3.249151095290975667e-3 * x)
                 + (-0.81236928277317888014 * v[0])
                 + (1.79937267839201497921 * v[1]);
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
