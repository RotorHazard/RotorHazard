#include "filter.h"

template <typename T> class NoFilter : public Filter<T>
{
    private:
        T v;
        mtime_t timestamp;
    public:
        bool isFilled() {
            return v != 0;
        }

        void addRawValue(mtime_t ts, T x)
        {
            timestamp = ts;
            v = x;
        }

        T getFilteredValue() {
            return v;
        }

        mtime_t getFilterTimestamp() {
            return timestamp;
        }
};
