/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Full URL of the API when the interface is hosted separately (including the
   *  /api suffix). Defaults to "/api". */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
