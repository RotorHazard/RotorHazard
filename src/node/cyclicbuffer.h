#ifndef cyclicbuffer_h
#define cyclicbuffer_h

template <typename T, uint8_t N> class CyclicBuffer {

public:
  void addLast(T value) {
      buffer[pos++] = value;
      if (pos >= N)
      {
          pos = 0;
      }
  }

  T getFirst() {
      return buffer[pos];
  }

  uint8_t getCapacity() {
      return N;
  }

private:
  T buffer[N];
  uint8_t pos = 0;
};

#endif
