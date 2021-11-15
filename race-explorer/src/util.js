import { useEffect, useRef } from 'react';

export function useInterval(callback, delay) {
  const savedCallbackRef = useRef();

  // Remember the latest callback.
  useEffect(() => {
    savedCallbackRef.current = callback;
  }, [callback]);

  // Set up the interval.
  useEffect(() => {
    function tick() {
      savedCallbackRef.current();
    }
    if (delay !== null) {
      let id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
}

export function formatTimeMillis(s, timeformat='{m}:{s}.{d}') {
  s = Math.round(s);
  let ms = s % 1000;
  s = (s - ms) / 1000;
  let secs = s % 60;
  let mins = (s - secs) / 60;

  if (!timeformat) {
    timeformat = '{m}:{s}.{d}';
  }
  let formatted_time = timeformat.replace('{d}', pad(ms, 3));
  formatted_time = formatted_time.replace('{s}', pad(secs));
  formatted_time = formatted_time.replace('{m}', mins)

  return formatted_time;
}

function pad(n, z=2) {
  return ('000000' + n).slice(-z);
}
