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

export function createBaseLoader() {
  const BaseLoader = {
    isCancelled: false,
    async load(processor, setState) {
      let data = this._getCached();
      let error = null;
      if (data === null) {
        try {
          data = await this._load(processor);
        } catch(err) {
          if (err?.name !== 'AbortError' && err?.message !== 'canceled') {
            error = () => {
              console.error(err.message);
            };
          }
        }
      }

      if (!this.isCancelled) {
        if (data !== null) {
          this._cache(data);
          setState(data);
        } else {
          error();
        }
      }
    },
    _getCached() {
      return null;
    },
    _cache(data) {},
    cancel() {
      this.isCancelled = true;
      this.aborter.abort();
    }
  };

  const loader = Object.create(BaseLoader);
  loader.aborter = new AbortController();
  return loader;
};

export function makeTopic(root, parts) {
  let topic = root;
  for (const part of parts) {
    let encodedPart;
    if (part === '+' || part === '#') {
      encodedPart = part;
    } else {
      encodedPart = part.replaceAll('%', '%25').replaceAll('/', '%2F').replaceAll('#', '%23').replaceAll('+', '%2B');
    }
    if (topic) {
      topic += '/';
    }
    topic += encodedPart;
  }
  return topic;
}

export function splitTopic(topic) {
  const parts = topic.split('/');
  for (let i=0; i<parts.length; i++) {
    parts[i] = parts[i].replace('%2B', '+').replace('%23', '#').replace('%2F', '/').replace('%25', '%');
  }
  return parts;
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
