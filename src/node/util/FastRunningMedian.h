#ifndef FASTRUNNINGMEDIAN_H
#define FASTRUNNINGMEDIAN_H

//
// Released to the public domain
//
// Remarks:
// This is a lean but fast version.
// Initially, the buffer is filled with a "default_value". To get real median values
// you have to fill the object with N values, where N is the size of the sliding window.
// For example: for(int i=0; i < 32; i++) myMedian.addValue(readSensor());
//
// Constructor:
// FastRunningMedian<datatype_of_content, size_of_sliding_window, default_value>
// maximim size_of_sliding_window is 255
// Methods:
// addValue(val) adds a new value to the buffers (and kicks the oldest)
// getMedian() returns the current median value
//
//
// Usage:
// #include "FastRunningMedian.h"
// FastRunningMedian<unsigned int,32, 0> myMedian;
// ....
// myMedian.addValue(value); // adds a value
// m = myMedian.getMedian(); // retieves the median
//

#include <inttypes.h>

template <typename T, uint8_t N, T default_value> class FastRunningMedian {

public:
	FastRunningMedian() {
		_buffer_ptr = N;
		_median_ptr = N/2;
		_unfilled = N;

		// Init buffers
		uint8_t i = N;
		while( i > 0 ) {
			i--;
			_inbuffer[i] = default_value;
			_sortbuffer[i] = default_value;
		}
	}

	bool isFilled() {
		return _unfilled == 0;
	}

	T getMedian() {
		// buffers are always sorted.
		return _sortbuffer[_median_ptr];
	}


	void addValue(T new_value) {
		if (_unfilled != 0)
			_unfilled--;

		// comparision with 0 is fast, so we decrement _buffer_ptr
		if (_buffer_ptr == 0)
			_buffer_ptr = N;

		_buffer_ptr--;

		T old_value = _inbuffer[_buffer_ptr]; // retrieve the old value to be replaced
		if (new_value == old_value) 		  // if the value is unchanged, do nothing
			return;

		_inbuffer[_buffer_ptr] = new_value;  // fill the new value in the cyclic buffer

		// search the old_value in the sorted buffer
		uint8_t i = N;
		while(i > 0) {
			i--;
			if (old_value == _sortbuffer[i])
				break;
		}

		// i is the index of the old_value in the sorted buffer
		_sortbuffer[i] = new_value; // replace the value

		// the sortbuffer is always sorted, except the [i]-element..
		if (new_value > old_value) {
			//  if the new value is bigger than the old one, make a bubble sort upwards
			for(uint8_t p=i, q=i+1; q < N; p++, q++) {
				// bubble sort step
				if (_sortbuffer[p] > _sortbuffer[q]) {
					T tmp = _sortbuffer[p];
					_sortbuffer[p] = _sortbuffer[q];
					_sortbuffer[q] = tmp;
				} else {
					// done ! - found the right place
					return;
				}
			}
		} else {
			// else new_value is smaller than the old one, bubble downwards
			for(int p=i-1, q=i; q > 0; p--, q--) {
				if (_sortbuffer[p] > _sortbuffer[q]) {
					T tmp = _sortbuffer[p];
					_sortbuffer[p] = _sortbuffer[q];
					_sortbuffer[q] = tmp;
				} else {
					// done !
					return;
				}
			}
		}
	}

private:
	// Pointer to the last added element in _inbuffer
	uint8_t _buffer_ptr;
	// position of the median value in _sortbuffer
	uint8_t _median_ptr;
	// number of unfilled entries in the buffer
	uint8_t _unfilled;

	// cyclic buffer for incoming values
	T _inbuffer[N];
	// sorted buffer
	T _sortbuffer[N];
};

// --- END OF FILE ---

#endif  //FASTRUNNINGMEDIAN_H
