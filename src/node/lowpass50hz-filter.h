#include "filter.h"
#include "cyclicbuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=50&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.05
class LowPassFilter50Hz : public Filter<rssi_t>
{
	public:
		LowPassFilter50Hz()
		{
		    v[0] = 0.0;
		    v[1] = 0.0;
		}
	private:
		uint8_t unfilled = 3;
		float v[3];
		rssi_t nextValue;
		CyclicBuffer<mtime_t,2> timestamps;
	public:
		bool isFilled() {
		    return unfilled == 0;
		}

		void addRawValue(mtime_t ts, rssi_t x)
		{
			if (unfilled != 0)
				unfilled--;

			v[0] = v[1];
			v[1] = v[2];
            v[2] = (2.921062558939069298e-2 * x)
                 + (-0.49774398476624526211 * v[0])
                 + (1.38090148240868249019 * v[1]);
			nextValue = (rssi_t)((v[0] + v[2]) + 2 * v[1]); // 2^

            timestamps.addLast(ts);
		}

		rssi_t getFilteredValue() {
		  return nextValue;
		}

		mtime_t getFilterTimestamp() {
		  return timestamps.getFirst();
		}
};
