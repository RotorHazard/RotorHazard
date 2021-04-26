#include "filter.h"

template <typename T> class NoFilter final : public Filter<T>
{
    private:
        T v;
        mtime_t timestamp;
    public:
        bool isFilled() const {
            return v != 0;
        }

        void addRawValue(mtime_t ts, T x) {
            timestamp = ts;
            v = x;
        }

        T getFilteredValue() const {
            return v;
        }

        mtime_t getFilterTimestamp() const {
            return timestamp;
        }

        void reset() {
            v = 0;
            timestamp = 0;
        }
};
