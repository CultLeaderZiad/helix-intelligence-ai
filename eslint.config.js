import js from '@eslint/js'
import react from 'eslint-plugin-react'

// Existing/native tools cannot parse JSX usage or enforce unused bindings.
// These rules cover the entire frontend; legacy violations remain failures.
export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  {
    files: ['src/**/*.{js,jsx,mjs}'],
    languageOptions: {
      ecmaVersion: 'latest', sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react },
    rules: {
      'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none', ignoreRestSiblings: true }],
      'react/jsx-uses-vars': 'error',
      'react/jsx-uses-react': 'error',
      'no-duplicate-imports': 'error',
      'no-unreachable': js.configs.recommended.rules['no-unreachable'],
    },
  },
]
