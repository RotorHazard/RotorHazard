#include <sys/time.h>

inline int sprints(char* dest, const char* src) {
  strcpy(dest, src);
  return strlen(src);
}

inline int jsonStart(char *buf) {
    buf[0] = '{';
    buf[1] = '\0';
    return 1;
}

inline int jsonPropertyString(char *buf, const char *key, const char *value) {
    int n = 0;
    buf[n++] = '\"';
    n += sprints(buf+n, key);
    buf[n++] = '\"';
    buf[n++] = ':';
    buf[n++] = ' ';
    buf[n++] = '\"';
    n += sprints(buf+n, value);
    buf[n++] = '\"';
    buf[n++] = '\0';
    return n;
}

inline int jsonPropertyUInt(char *buf, const char *key, int value) {
    int n = 0;
    buf[n++] = '\"';
    n += sprints(buf+n, key);
    buf[n++] = '\"';
    buf[n++] = ':';
    buf[n++] = ' ';
    n += sprintf(buf+n, "%u", value);
    return n;
}

inline int jsonPropertyNegUInt(char *buf, const char *key, int value) {
    int n = 0;
    buf[n++] = '\"';
    n += sprints(buf+n, key);
    buf[n++] = '\"';
    buf[n++] = ':';
    buf[n++] = ' ';
    n += sprintf(buf+n, "-%u", value);
    return n;
}

inline int jsonPropertyTime(char *buf, const char *key, const timeval *t) {
    int n = 0;
    buf[n++] = '\"';
    n += sprints(buf+n, key);
    buf[n++] = '\"';
    buf[n++] = ':';
    buf[n++] = ' ';
    n += sprintf(buf+n, "%ld%ld", t->tv_sec, t->tv_usec/1000L);
    return n;
}

inline int jsonEnd(char *buf) {
    buf[0] = '}';
    buf[1] = '\0';
    return 1;
}
