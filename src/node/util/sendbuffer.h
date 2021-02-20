#ifndef sendbuffer_h
#define sendbuffer_h

template <typename  T> class SendBuffer {
    public:
        virtual bool addPeak(const T& peak, bool force) = 0;
        virtual bool addNadir(const T& nadir, bool force) = 0;
        virtual const T nextPeak() = 0;
        virtual const T nextNadir() = 0;
        virtual ExtremumType nextType() = 0;
        virtual const T popNext() = 0;
        virtual void clear() = 0;
};

class ExtremumSendBuffer {
    public:
        virtual bool isEmpty() = 0;
        virtual bool isFull() = 0;
        bool addIfAvailable(const Extremum& e) {
            if (!isFull()) {
                add(e);
                return true;
            } else {
                return false;
            }
        }
        virtual void addOrDiscard(const Extremum& e) = 0;
        virtual const Extremum first() = 0;
        virtual void removeFirst() = 0;
        virtual void clear() = 0;
    protected:
        virtual void add(const Extremum& e) = 0;
};

class DualSendBuffer: public SendBuffer<Extremum> {
    private:
        ExtremumSendBuffer *peakBuffer;
        ExtremumSendBuffer *nadirBuffer;
    public:
        DualSendBuffer(ExtremumSendBuffer *pb, ExtremumSendBuffer *nb) : peakBuffer(pb), nadirBuffer(nb) {
        }

        bool addPeak(const Extremum& peak, bool force) {
            bool buffered = peakBuffer->addIfAvailable(peak);
            if (!buffered && force)
            {
                peakBuffer->addOrDiscard(peak);
                buffered = true;
            }
            return buffered;
        }
        bool addNadir(const Extremum& nadir, bool force) {
            bool buffered = nadirBuffer->addIfAvailable(nadir);
            if (!buffered && force)
            {
                nadirBuffer->addOrDiscard(nadir);
                buffered = true;
            }
            return buffered;
        }
        const Extremum nextPeak() {
            return peakBuffer->first();
        }
        const Extremum nextNadir() {
            return nadirBuffer->first();
        }
        ExtremumType nextType() {
            if (!peakBuffer->isEmpty() && (nadirBuffer->isEmpty() || (peakBuffer->first().firstTime < nadirBuffer->first().firstTime)))
            {
                return PEAK;
            }
            else if(!nadirBuffer->isEmpty() && (peakBuffer->isEmpty() || (nadirBuffer->first().firstTime < peakBuffer->first().firstTime)))
            {
                return NADIR;
            }
            else
            {
                return NONE;
            }
        }
        const Extremum popNext() {
            Extremum e = {0, 0, 0};
            switch (nextType())
            {
                case PEAK:
                    e = peakBuffer->first();
                    peakBuffer->removeFirst();
                    break;
                case NADIR:
                    e = nadirBuffer->first();
                    nadirBuffer->removeFirst();
                    break;
            }
            return e;
        }
        void clear() {
            peakBuffer->clear();
            nadirBuffer->clear();
        }
};

#endif
