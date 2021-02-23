/*
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU Lesser General Public License as
 published by the Free Software Foundation, either version 3 of the
 License, or (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
#ifndef LISTS_H_
#define LISTS_H_

#include "Collections.h"

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class ArrayList : public List<T,S,IT> {
private:
    const T *const buffer;
public:
    ArrayList(T arr[]) : buffer(arr) {

    }
    T inline operator [](IT index) const {
        return buffer[index];
    }
    IT inline size() const {
        return S;
    }
};

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class SlicedList : public List<T,S,IT> {
private:
    const List<T,S,IT>& buffer;
    const IT start, end;
public:
    SlicedList(List<T,S,IT>& l, IT start, IT end) : buffer(l), start(start), end(end) {

    }
    T inline operator [](IT index) const {
        return buffer[start+index];
    }
    IT inline size() const {
        return end - start;
    }
};

#endif
