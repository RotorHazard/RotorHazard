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

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class ArrayList final : public List<T,S,IT> {
private:
    const T *const buffer;
public:
    ArrayList(const T arr[]) : buffer(arr) {

    }
    T inline operator [](IT index) const {
        return buffer[index];
    }
    IT inline size() const {
        return S;
    }
};

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class SlicedList final : public List<T,S,IT> {
private:
    const List<T,S,IT>& buffer;
    const IT start, end;
public:
    SlicedList(const List<T,S,IT>& l, IT start, IT end) : buffer(l), start(start), end(end) {

    }
    T inline operator [](IT index) const {
        return buffer[start+index];
    }
    IT inline size() const {
        return end - start;
    }
};

template<typename T, size_t S1, size_t S2, typename IT = typename Helper::Index<(S1+S2 <= UINT8_MAX), (S1+S2 <= UINT16_MAX)>::Type> class CompoundList final : public List<T,S1+S2,IT> {
private:
    const List<T,S1,IT>& l1;
    const List<T,S2,IT>& l2;
public:
    CompoundList(const List<T,S1,IT>& l1, const List<T,S2,IT>& l2) : l1(l1), l2(l2) {

    }
    T inline operator [](IT index) const {
        return (index >= 0 && index < l1.size()) ? l1[index] : l2[index-l1.size()];
    }
    IT inline size() const {
        return l1.size() + l2.size();
    }
};

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class PreList final : public List<T,S+1,IT> {
private:
    const T& v;
    const List<T,S,IT>& l;
public:
    PreList(const T& v, const List<T,S,IT>& l) : v(v), l(l) {

    }
    T inline operator [](IT index) const {
        return (index >= 1 && index < l.size()+1) ? l[index-1] : v;
    }
    IT inline size() const {
        return l.size() + 1;
    }
};

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class PostList final : public List<T,S+1,IT> {
private:
    const List<T,S,IT>& l;
    const T& v;
public:
    PostList(const List<T,S,IT>& l, const T& v) : l(l), v(v) {

    }
    T inline operator [](IT index) const {
        return (index >= 0 && index < l.size()) ? l[index] : v;
    }
    IT inline size() const {
        return l.size() + 1;
    }
};

#endif
