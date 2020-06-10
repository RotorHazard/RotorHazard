#ifndef sendbuffer_h
#define sendbuffer_h

template <typename T> class SendBuffer {

public:
  virtual bool isEmpty() = 0;
  virtual bool isFull() = 0;
  bool addIfAvailable(const T& e) {
      if (!isFull()) {
          add(e);
          return true;
      } else {
          return false;
      }
  }
  virtual void addOrDiscard(const T& e) = 0;
  virtual const T first() = 0;
  virtual void removeFirst() = 0;
  virtual void clear() = 0;
protected:
  virtual void add(const T& e) = 0;
};

#endif
