/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
  readonly VITE_PORT: string
  readonly VITE_ENABLE_DEBUG: string
  readonly VITE_ENABLE_FILE_UPLOAD: string
  readonly VITE_ENABLE_ANALYTICS: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Global constants defined in vite.config.ts
declare const __APP_VERSION__: string
declare const __API_URL__: string
declare const __BUILD_DATE__: string
