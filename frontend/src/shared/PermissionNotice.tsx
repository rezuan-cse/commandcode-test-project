import type { ReactNode } from "react";
import { canRead, canWrite, denialMessage } from "./permissions";
import type { Access } from "./types";

/**
 * Shown in place of a screen or form the signed-in role may not use.
 *
 * Replaces a raw refusal such as "Role 'Accountant' does not have write access
 * to 'sales_purchase'", which named an internal identifier the reader has never
 * seen and offered no way forward.
 */
export function PermissionNotice({
  role,
  resource,
  write,
  level,
  readableBelow = false,
}: {
  role: string;
  resource: string;
  write: boolean;
  level: Access | undefined;
  /** Only claim there is something to read when the screen really shows one. */
  readableBelow?: boolean;
}) {
  return (
    <div className="permission-notice">
      <span className="permission-mark" aria-hidden="true">
        !
      </span>
      <div>
        <div className="permission-title">
          {write && canRead(level)
            ? "View only for your role"
            : "Not available for your role"}
        </div>
        <div className="permission-body">
          {denialMessage(role, resource, level, write)}
        </div>
        {write && canRead(level) && (
          <div className="permission-hint">
            {readableBelow
              ? "You can still read what has already been posted, below. "
              : ""}
            Sign in as an administrator if you need to make changes.
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Gate a screen behind a permission.
 *
 * Renders the notice instead of the children when the role lacks the access
 * required, so an unreachable screen shows an explanation rather than an error
 * from a failed request.
 */
export function RequirePermission({
  role,
  resource,
  write = false,
  level,
  children,
}: {
  role: string;
  resource: string;
  write?: boolean;
  level: Access | undefined;
  children: ReactNode;
}) {
  const allowed = write ? canWrite(level) : canRead(level);
  if (allowed) return <>{children}</>;
  return (
    <>
      <h1>{denialTitle(write, level)}</h1>
      <PermissionNotice role={role} resource={resource} write={write} level={level} />
    </>
  );
}

function denialTitle(write: boolean, level: Access | undefined): string {
  if (write && canRead(level)) return "View only";
  return "Not available";
}
