#include "filter.h"

template <typename T> class Composite2Filter : public Filter<T>
{
    private:
        Filter<T>& f1;
        Filter<T>& f2;
    public:
        Composite2Filter(Filter<T>& f1, Filter<T>& f2): f1(f1), f2(f2) {
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

        void reset() {
            f1.reset();
            f2.reset();
        }
};

template <typename T> class Composite3Filter : public Filter<T>
{
    private:
        Filter<T>& f1;
        Filter<T>& f2;
        Filter<T>& f3;
    public:
        Composite3Filter(Filter<T>& f1, Filter<T>& f2, Filter<T>& f3): f1(f1), f2(f2), f3(f3) {
        }

        bool isFilled() {
            return f1.isFilled() && f2.isFilled() && f3.isFilled();
        }

        void addRawValue(mtime_t ts, T x)
        {
            f1.addRawValue(ts, x);
            if (f1.isFilled()) {
                f2.addRawValue(f1.getFilterTimestamp(), f1.getFilteredValue());
                if (f2.isFilled()) {
                    f3.addRawValue(f2.getFilterTimestamp(), f2.getFilteredValue());
                }
            }
        }

        T getFilteredValue() {
            return f3.getFilteredValue();
        }

        mtime_t getFilterTimestamp() {
            return f3.getFilterTimestamp();
        }

        void reset() {
            f1.reset();
            f2.reset();
            f3.reset();
        }
};
