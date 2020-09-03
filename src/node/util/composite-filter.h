#include "filter.h"

template <typename T> class CompositeFilter : public Filter<T>
{
    private:
        Filter<T>& f1;
        Filter<T>& f2;
    public:
        CompositeFilter(Filter<T>& f1, Filter<T>& f2): f1(f1), f2(f2) {
        }

        bool isFilled() {
            return f1.isFilled() && f2.isFilled();
        }

        void addRawValue(mtime_t ts, T x)
        {
            f1.addRawValue(ts, x);
            if (f1.isFilled()) {
                f2.addRawValue(f1.getFilterTimestamp(), f1.getFilteredValue());
            }
        }

        T getFilteredValue() {
            return f2.getFilteredValue();
        }

        mtime_t getFilterTimestamp() {
          return f2.getFilterTimestamp();
        }
};
