import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";

/**
 * Session-wide view state: the reporting period, and a revision counter used to
 * refetch after a posting.
 *
 * The acting role used to live here. It now comes from the signed-in user in
 * AuthContext, because the server derives permissions from the token rather than
 * from anything the browser claims.
 */
interface DemoState {
  asOf: string;
  dateFrom: string;
  setAsOf: (value: string) => void;
  setDateFrom: (value: string) => void;
  /** Bumped to force dependent screens to refetch after a posting. */
  revision: number;
  refresh: () => void;
}

function isoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/**
 * What to show before the server has answered.
 *
 * These used to be the sample workbook's dates, so a company with no workbook
 * posted every transaction dated 2026-10-31 unless it noticed the top bar. The
 * server sends the real period — the latest posting if there is history, otherwise
 * today — and it replaces these as soon as it arrives. July is the Bangladesh
 * fiscal year start, matching the setting the server sends.
 */
function fiscalStartFallback(): string {
  const today = new Date();
  const year = today.getMonth() + 1 >= 7 ? today.getFullYear() : today.getFullYear() - 1;
  return `${year}-07-01`;
}

const DemoContext = createContext<DemoState | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [asOf, setAsOfState] = useState(() => isoDate(new Date()));
  const [dateFrom, setDateFromState] = useState(fiscalStartFallback);
  // Once the user picks a period, the server's suggestion must not overwrite it.
  const touched = useRef(false);

  useEffect(() => {
    let cancelled = false;
    api
      .meta()
      .then((meta) => {
        if (cancelled || touched.current) return;
        // Only trust a well-formed answer: a partial response must not blank the
        // period, which would leave every report querying with no date at all.
        if (typeof meta?.suggested_as_of === "string") setAsOfState(meta.suggested_as_of);
        if (typeof meta?.suggested_from === "string") setDateFromState(meta.suggested_from);
      })
      .catch(() => {
        // Leave the local fallback in place; the screens still work.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const [revision, setRevision] = useState(0);

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  const setAsOf = useCallback((value: string) => {
    touched.current = true;
    setAsOfState(value);
  }, []);

  const setDateFrom = useCallback((value: string) => {
    touched.current = true;
    setDateFromState(value);
  }, []);

  const value = useMemo(
    () => ({ asOf, dateFrom, setAsOf, setDateFrom, revision, refresh }),
    [asOf, dateFrom, setAsOf, setDateFrom, revision, refresh],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo(): DemoState {
  const context = useContext(DemoContext);
  if (!context) throw new Error("useDemo must be used inside DemoProvider");
  return context;
}
