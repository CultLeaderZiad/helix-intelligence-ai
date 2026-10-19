import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: {
    // The node:test W0/W1 suites run separately in the package test script.
    include: ['src/**/__tests__/*w3*.{js,jsx}', 'src/**/__tests__/*w4*.{js,jsx}'],
    environment: 'jsdom',
  },
})
