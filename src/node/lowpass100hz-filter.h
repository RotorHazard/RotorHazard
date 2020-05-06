#include "filter.h"
#define CIRCULAR_BUFFER_INT_SAFE
#include "CircularBuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=100&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.1
class LowPassFilter100Hz : public Filter<rssi_t>
{
	private:
		uint8_t unfilled = 3;
		float v[3];
		rssi_t nextValue;
		CircularBuffer<mtime_t,2> timestamps;
	public:
        LowPassFilter100Hz()
        {
            v[0] = 0.0;
            v[1] = 0.0;
        }

        bool isFilled() {
		    return unfilled == 0;
		}

		void addRawValue(mtime_t ts, rssi_t x)
		{
			if (unfilled != 0)
				unfilled--;

			v[0] = v[1];
			v[1] = v[2];
            v[2] = (9.053999669813994622e-2 * x)
                 + (-0.24114073878907091308 * v[0])
                 + (0.87898075199651115597 * v[1]);
            nextValue = (rssi_t)((v[0] + v[2]) + 2 * v[1]); // 2^

            timestamps.push(ts);
		}

		rssi_t getFilteredValue() {
		  return nextValue;
		}

		mtime_t getFilterTimestamp() {
		  return timestamps.first();
		}
};
