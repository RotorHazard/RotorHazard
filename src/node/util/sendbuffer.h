#ifndef sendbuffer_h
#define sendbuffer_h

#include "Collections.h"

template <typename  T> class SendBuffer : public Collection<uint_fast8_t> {
    public:
        virtual bool addPeak(const T& peak, bool force = false) = 0;
        virtual bool addNadir(const T& nadir, bool force = false) = 0;
        /** mainly used for testing */
        virtual const T nextPeak() const = 0;
        /** mainly used for testing */
        virtual const T nextNadir() const = 0;
        virtual const ExtremumType nextType() const = 0;
        virtual const T popNext() = 0;
        virtual void clear() = 0;
};

class ExtremumSendBuffer : public Collection<uint_fast8_t> {
    public:
        virtual bool isEmpty() const = 0;
        virtual bool isFull() const = 0;
        bool addIfAvailable(const Extremum& e) {
            if (!isFull()) {
                add(e);
                return true;
            } else {
                return false;
            }
        }
        virtual void addOrDiscard(const Extremum& e, bool wasLast) = 0;
        virtual const Extremum first() const = 0;
        virtual const Extremum last() const = 0;
        virtual void removeFirst() = 0;
        virtual void clear() = 0;
    protected:
        virtual void add(const Extremum& e) = 0;
};

class DualSendBuffer: public SendBuffer<Extremum> {
    private:
        ExtremumSendBuffer *peakBuffer;
        ExtremumSendBuffer *nadirBuffer;
        ExtremumType lastType() const {
            if (!peakBuffer->isEmpty() && (nadirBuffer->isEmpty() || (peakBuffer->last().firstTime > nadirBuffer->last().firstTime)))
            {
                return PEAK;
            }
            else if(!nadirBuffer->isEmpty() && (peakBuffer->isEmpty() || (nadirBuffer->last().firstTime > peakBuffer->last().firstTime)))
            {
                return NADIR;
            }
            else
            {
                return NONE;
            }
        }
    public:
        void setSendBuffers(ExtremumSendBuffer *pbuf, ExtremumSendBuffer *nbuf) {
            peakBuffer = pbuf;
            nadirBuffer = nbuf;
        }

        uint_fast8_t size() const {
            return peakBuffer->size() + nadirBuffer->size();
        }
        bool addPeak(const Extremum& peak, bool force = false) {
            bool buffered = peakBuffer->addIfAvailable(peak);
            if (!buffered && force)
            {
                peakBuffer->addOrDiscard(peak, lastType() == PEAK);
                buffered = true;
            }
            return buffered;
        }
        bool addNadir(const Extremum& nadir, bool force = false) {
            bool buffered = nadirBuffer->addIfAvailable(nadir);
            if (!buffered && force)
            {
                nadirBuffer->addOrDiscard(nadir, lastType() == NADIR);
                buffered = true;
            }
            return buffered;
        }
        const Extremum nextPeak() const {
            return peakBuffer->first();
        }
        const Extremum nextNadir() const {
            return nadirBuffer->first();
        }
        const ExtremumType nextType() const {
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
                default:
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
