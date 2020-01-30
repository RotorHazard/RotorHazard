#include "filter.h"
#include "cyclicbuffer.h"

/*
 * Based on
 * http://www.schwietering.com/jayduino/filtuino/index.php?characteristic=be&passmode=lp&order=2&usesr=usesr&sr=1000&frequencyLow=20&noteLow=&noteHigh=&pw=pw&calctype=float&run=Send
 */

//Low pass bessel filter order=2 alpha1=0.02
class LowPassFilter20Hz : public Filter<rssi_t>
{
	public:
		LowPassFilter20Hz()
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
            v[2] = (5.593440209108096160e-3 * x)
                 + (-0.75788377219702429688 * v[0])
                 + (1.73551001136059190877 * v[1]);
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

LowPassFilter20Hz _filter;
