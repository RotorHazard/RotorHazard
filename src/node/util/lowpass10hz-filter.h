#include "filter.h"
#include "CircularBuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=10&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.01
//constant delay in the pass-band (variably less above)
class LowPassFilter10Hz final : public Filter<rssi_t>
{
    private:
        float v[3];
        rssi_t nextValue;
        CircularBuffer<mtime_t,21> timestamps; // delay correct for pass-band
    public:
        LowPassFilter10Hz()
        {
            v[0] = 0.0;
            v[1] = 0.0;
        }

        bool isFilled() const {
            return timestamps.isFull();
        }

        void addRawValue(mtime_t ts, rssi_t x)
        {
            v[0] = v[1];
            v[1] = v[2];
            v[2] = (1.492279154364811733e-3 * x)
                 + (-0.87068345511128286685 * v[0])
                 + (1.86471433849382361991 * v[1]);
            nextValue = (rssi_t)((v[0] + v[2]) + 2 * v[1]);

            timestamps.push(ts);
        }

        rssi_t getFilteredValue() const {
            return nextValue;
        }

        mtime_t getFilterTimestamp() const {
            return timestamps.first();
        }

        void reset() {
            v[0] = 0.0;
            v[1] = 0.0;
            v[2] = 0.0;
            nextValue = 0;
            timestamps.clear();
        }
};
