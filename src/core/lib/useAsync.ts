import { useCallback, useEffect, useState } from 'react';

export type AsyncState<T> = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: T };

/** Runs an abortable request on mount, with a retry function for error states. */
export function useAsync<T>(fn: (signal: AbortSignal) => Promise<T>): [AsyncState<T>, () => void] {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    fn(ctrl.signal)
      .then((data) => setState({ status: 'ready', data }))
      .catch((err: Error) => {
        if (err.name !== 'AbortError') setState({ status: 'error', message: err.message });
      });
    return () => ctrl.abort();
    // fn is a stable module-level function in our usage; re-run only on retry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ status: 'loading' });
    setAttempt((n) => n + 1);
  }, []);

  return [state, retry];
}
