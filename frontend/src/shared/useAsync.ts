/** Fetches data and re-runs whenever the demo revision changes. */

import { useEffect, useState } from "react";
import { useDemo } from "./DemoContext";

export interface AsyncResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * Run an async loader, refreshing on every demo revision (which is bumped
 * after any posting) and whenever the dependency list changes.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncResult<T> {
  const { revision } = useDemo();
  const [state, setState] = useState<AsyncResult<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((current) => ({ ...current, loading: true, error: null }));
    loader()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, revision]);

  return state;
}
