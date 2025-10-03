import { fileURLToPath, URL } from 'node:url'
import { writeFileSync } from 'fs'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import svgLoader from 'vite-svg-loader'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import { resolve } from 'path'

function createUpdateDatePlugin() {
  return {
    name: 'create-update-date',
    buildStart() {
      const updateData = {
        lastUpdate: new Date().toISOString(),
      }
      const filePath = resolve(process.cwd(), 'public', 'updDate.json')
      writeFileSync(filePath, JSON.stringify(updateData, null, 2))
      console.log(`✅ updDate.json created: ${updateData.lastUpdate}`)
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueJsx(),
    createUpdateDatePlugin(),
    svgLoader({
      svgo: false,
      // svgoConfig: {
      //   multipass: false,
      //   plugins: [
      //     'preset-default',
      //     'prefixIds',
      //     {
      //       name: 'prefixIds',
      //       params: {
      //         overrides: {
      //           removeViewBox: false,
      //           inlineStyles: {
      //             onlyMatchedOnce: false,
      //           }
      //         }
      //       }
      //      },
      //   ],
      // }
    }),
    nodePolyfills(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
