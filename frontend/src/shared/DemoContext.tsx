import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

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

// The workbook's own reporting date, so the demo opens on familiar figures.
const DEFAULT_AS_OF = "2026-10-31";
const DEFAULT_FROM = "2026-01-01";

const DemoContext = createContext<DemoState | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [asOf, setAsOf] = useState(DEFAULT_AS_OF);
  const [dateFrom, setDateFrom] = useState(DEFAULT_FROM);
  const [revision, setRevision] = useState(0);

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  const value = useMemo(
    () => ({ asOf, dateFrom, setAsOf, setDateFrom, revision, refresh }),
    [asOf, dateFrom, revision, refresh],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo(): DemoState {
  const context = useContext(DemoContext);
  if (!context) throw new Error("useDemo must be used inside DemoProvider");
  return context;
}
