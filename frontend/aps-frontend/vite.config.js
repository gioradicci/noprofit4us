import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Markdown from 'unplugin-vue-markdown/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      include: [/\.vue$/, /\.md$/]   // abilita .md come componenti Vue
    }),
    Markdown({
      markdownOptions: {
        html: true,
        linkify: true,
        typographer: true
      }
    })
  ],
})

