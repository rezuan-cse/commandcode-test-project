/** Small presentational building blocks shared by every screen. */

import { useState, type ReactNode } from "react";

import { downloadCsv, toCsv, type CsvColumn } from "./csv";

export function Card({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="muted small">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "positive" | "negative";
}) {
  return (
    <div className={`stat stat-${tone}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "positive" | "negative" | "warn" | "info";
}) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

/**
 * A button that downloads the rows it is given as a CSV file.
 *
 * The screen decides which columns and which values: a list passes its loaded
 * rows, a report passes its own. Figures are written as they are stored rather
 * than as displayed, so they sum in Excel — see `shared/csv.ts`.
 *
 * What it exports is exactly what the screen holds. Where a list is capped by the
 * API's page limit, the file is capped with it, so the button says so rather than
 * quietly producing a short file.
 */
export function ExportButton<T>({
  filename,
  columns,
  rows,
}: {
  filename: string;
  columns: CsvColumn<T>[];
  rows: T[] | null | undefined;
}) {
  const data = rows ?? [];
  return (
    <button
      type="button"
      onClick={() => downloadCsv(filename, toCsv(columns, data))}
      disabled={data.length === 0}
      title={
        data.length === 0
          ? "Nothing to export yet"
          : `Download these ${data.length} row(s) as a CSV file, which opens in Excel`
      }
    >
      Export CSV
    </button>
  );
}

/**
 * The Resinova logo.
 *
 * Two files from the brand kit belong in `frontend/public`:
 *
 *   `resinova-logo-light.svg` — the lockup for white backgrounds, with the
 *                               charcoal wordmark. Used on the sign-in panel.
 *   `resinova-logo-dark.svg`  — the reverse lockup for the charcoal sidebar,
 *                               with the white wordmark and the blue R.
 *
 * Until a file is in place the wordmark is drawn in text instead, so a missing
 * file shows as a plain name rather than a broken image. Adding the artwork is
 * then the only step left.
 */
export function Logo({ variant }: { variant: "light" | "dark" }) {
  const [missing, setMissing] = useState(false);

  if (missing) {
    return (
      <span className="brand-mark">
        <span className="brand-r">R</span>esinova
      </span>
    );
  }
  return (
    <img
      className={`brand-logo brand-logo-${variant}`}
      src={`/resinova-logo-${variant}.svg`}
      alt="Resinova"
      onError={() => setMissing(true)}
    />
  );
}

/**
 * An on/off switch.
 *
 * Used where a value is a state rather than a choice — a configuration rule that
 * is on or off, an employee who is active or has left. A tick box is kept
 * underneath, so the control is still a real checkbox to a keyboard, a screen
 * reader and the tests; the track and knob are drawn on top of it.
 */
export function Toggle({
  checked,
  onChange,
  labelOn = "on",
  labelOff = "off",
  disabled = false,
  ariaLabel,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  labelOn?: string;
  labelOff?: string;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  return (
    <label className={`toggle${disabled ? " disabled" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        aria-label={ariaLabel}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="toggle-track" aria-hidden="true" />
      <span className="toggle-text">{checked ? labelOn : labelOff}</span>
    </label>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="spinner">{label}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="error-box">{message}</div>;
}

export function Empty({ message }: { message: string }) {
  return <div className="empty">{message}</div>;
}
