#include "filter.h"
#include "CircularBuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=100&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.1
//constant delay in the pass-band (variably less above)
class LowPassFilter100Hz final : public Filter<rssi_t>
{
    private:
        float v[3];
        rssi_t nextValue;
        CircularBuffer<mtime_t,3> timestamps; // delay correct for pass-band
    public:
        LowPassFilter100Hz()
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
            v[2] = (9.053999669813994622e-2 * x)
                 + (-0.24114073878907091308 * v[0])
                 + (0.87898075199651115597 * v[1]);
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
