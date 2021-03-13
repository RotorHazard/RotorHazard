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
#ifndef COLLECTIONS_H_
#define COLLECTIONS_H_

namespace Helper {
    template<bool FITS8, bool FITS16> struct Index {
        using Type = uint_fast32_t;
    };

    template<> struct Index<false, true> {
        using Type = uint_fast16_t;
    };

    template<> struct Index<true, true> {
        using Type = uint_fast8_t;
    };
}

template<typename IT> class Collection {
public:
    virtual IT size() const = 0;
};

template<typename T, size_t S, typename IT = typename Helper::Index<(S <= UINT8_MAX), (S <= UINT16_MAX)>::Type> class List : public Collection<IT> {
public:
    virtual T operator [] (IT index) const = 0;
};

#define CIRCULAR_BUFFER_INT_SAFE

#endif
