"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Runs `fn` whenever `key` changes. `data` and `error` are null while the
 * request for the current key is in flight, so stale results never show.
 */
export function useAsync<T>(fn: () => Promise<T>, key: string) {
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ id: string; data?: T; error?: string } | null>(null);
  const id = `${key}#${attempt}`;

  useEffect(() => {
    let alive = true;
    fnRef.current()
      .then((data) => alive && setState({ id, data }))
      .catch((e: Error) => alive && setState({ id, error: e.message }));
    return () => {
      alive = false;
    };
  }, [id]);

  const current = state?.id === id ? state : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    retry: () => setAttempt((a) => a + 1),
  };
}
