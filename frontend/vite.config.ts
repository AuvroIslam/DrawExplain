import { createReadStream, existsSync, statSync } from 'node:fs'
import { cp } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const ROOT = path.dirname(fileURLToPath(import.meta.url))
const FONTS_DIR = path.join(ROOT, 'node_modules/@excalidraw/excalidraw/dist/prod/fonts')

/** Self-host Excalidraw's fonts at /fonts/ (index.html sets EXCALIDRAW_ASSET_PATH = "/"),
 *  so the whiteboard renders its hand-drawn font without the CDN (offline demos). */
function excalidrawFonts(): Plugin {
  const serve = (url: string | undefined, res: import('node:http').ServerResponse, next: () => void) => {
    const rel = decodeURIComponent((url ?? '').split('?')[0]).replace(/^\/+/, '')
    const file = path.join(FONTS_DIR, rel)
    if (!file.startsWith(FONTS_DIR) || !existsSync(file) || !statSync(file).isFile()) return next()
    res.setHeader('Content-Type', file.endsWith('.woff2') ? 'font/woff2' : 'application/octet-stream')
    res.setHeader('Cache-Control', 'public, max-age=86400')
    createReadStream(file).pipe(res)
  }
  let outDir = path.join(ROOT, 'dist')
  return {
    name: 'studylens-excalidraw-fonts',
    configResolved(config) {
      outDir = path.resolve(config.root, config.build.outDir)
    },
    configureServer(server) {
      server.middlewares.use('/fonts', (req, res, next) => serve(req.url, res, next))
    },
    configurePreviewServer(server) {
      server.middlewares.use('/fonts', (req, res, next) => serve(req.url, res, next))
    },
    async closeBundle() {
      if (existsSync(FONTS_DIR)) await cp(FONTS_DIR, path.join(outDir, 'fonts'), { recursive: true })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), excalidrawFonts()],
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  preview: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 4096,
  },
})
