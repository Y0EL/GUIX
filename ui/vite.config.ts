import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import cesium from 'vite-plugin-cesium'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import fs from 'fs'

export default defineConfig({
  plugins: [
    react(),
    cesium(),
    tailwindcss(),
    // Sajikan folder /news/ dari root project (gambar berita, HTML, dsb.)
    {
      name: 'serve-news-static',
      configureServer(server) {
        server.middlewares.use('/news', (req, res, next) => {
          const filePath = path.join(__dirname, '..', 'news', req.url ?? '')
          if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            res.setHeader('Cache-Control', 'no-cache')
            fs.createReadStream(filePath).pipe(res)
          } else {
            next()
          }
        })
      },
    },
  ],
})
