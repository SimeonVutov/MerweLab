import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig, normalizePath } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

const cesiumSource = normalizePath(fileURLToPath(
  new URL('./node_modules/cesium/Build/Cesium/', import.meta.url),
));

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: ['Workers', 'ThirdParty', 'Assets', 'Widgets'].map((directory) => ({
        src: `${cesiumSource}${directory}`,
        dest: 'cesium',
      })),
    }),
    viteStaticCopy({
      targets: ['buildings', 'surfaces', 'terrain', 'context'].map((directory) => ({
        src: normalizePath(fileURLToPath(new URL(`../../data/web/${directory}`, import.meta.url))),
        dest: 'web',
      })),
    }),
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium/'),
  },
});
