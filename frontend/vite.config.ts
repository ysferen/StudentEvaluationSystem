import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: react(),

    // Path resolution
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@pages': path.resolve(__dirname, './src/pages'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@services': path.resolve(__dirname, './src/services'),
        '@types': path.resolve(__dirname, './src/types'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@api': path.resolve(__dirname, './src/api'),
      },
    },

    // Development server configuration
    server: {
      port: env.VITE_PORT ? Number(env.VITE_PORT) : 5173,
      strictPort: false,
      host: true,

      // Proxy API requests to Django backend
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          // Don't rewrite path - keep /api prefix
          rewrite: (path) => path,
          // Log proxied requests in debug mode
          configure: (proxy, options) => {
            proxy.on('proxyReq', (_proxyReq, req, _res) => {
              if (env.VITE_ENABLE_DEBUG === 'true') {
                const target = options.target?.toString() ?? ''
                const requestUrl = req.url ?? ''
                console.log('[Proxy]', req.method, requestUrl, '→', target + requestUrl)
              }
            })
          },
        },
        // Proxy media files (user uploads, etc.)
        '/media': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        // Proxy static files if needed
        '/static': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },

    // Build configuration
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',

      // Code splitting for better caching
      rollupOptions: {
        output: {
          manualChunks: (id: string) => {
            if (id.includes('node_modules')) {
              if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
                return 'react-vendor'
              }
              if (id.includes('@tanstack/react-query')) {
                return 'query-vendor'
              }
              if (id.includes('react-apexcharts') || id.includes('apexcharts')) {
                return 'charts'
              }
              if (id.includes('@heroicons/react')) {
                return 'icons'
              }
              if (id.includes('axios')) {
                return 'vendor'
              }
            }

            return undefined
          },
        },
      },

      // Chunk size warnings
      chunkSizeWarningLimit: 1000, // 1MB

      // Enable gzip size reporting
      reportCompressedSize: true,
    },

    // Define global constants (available in code)
    define: {
      __APP_VERSION__: JSON.stringify(env.VITE_APP_VERSION || '1.0.0'),
      __API_URL__: JSON.stringify(env.VITE_API_URL),
      __BUILD_DATE__: JSON.stringify(new Date().toISOString()),
    },

    // Optimize dependencies
    optimizeDeps: {
      include: ['react', 'react-dom', 'react-router-dom', 'axios'],
    },
  }
})
