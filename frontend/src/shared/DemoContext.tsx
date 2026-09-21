import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getActingRole, setActingRole } from "./api";

/**
 * Session-wide demo state: the reporting period and the role being
 * impersonated. The role is pushed into the API client so every request
 * carries it, which is what makes server-side permission checks visible.
 */
interface DemoState {
  asOf: string;
  dateFrom: string;
  setAsOf: (value: string) => void;
  setDateFrom: (value: string) => void;
  role: string;
  setRole: (value: string) => void;
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
  const [role, setRoleState] = useState(getActingRole());
  const [revision, setRevision] = useState(0);

  const setRole = useCallback((value: string) => {
    setActingRole(value);
    setRoleState(value);
  }, []);

  const refresh = useCallback(() => setRevision((current) => current + 1), []);

  const value = useMemo(
    () => ({ asOf, dateFrom, setAsOf, setDateFrom, role, setRole, revision, refresh }),
    [asOf, dateFrom, role, setRole, revision, refresh],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo(): DemoState {
  const context = useContext(DemoContext);
  if (!context) throw new Error("useDemo must be used inside DemoProvider");
  return context;
}
