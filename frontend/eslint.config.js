/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          args: 'after-used',
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrors: 'all',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
      // eslint-plugin-react-hooks v7 enables the React Compiler rule set in its
      // recommended config. This project does NOT use the React Compiler
      // (vite.config.ts uses the plain @vitejs/plugin-react with no
      // babel-plugin-react-compiler), so these compiler-readiness lints flag
      // idiomatic, correct code (fetch-on-mount, reset-on-open, Date.now() in
      // render, etc.) for an optimization pass that never runs. Disable the
      // compiler-only rules; keep the classic, always-applicable hook rules
      // (rules-of-hooks = error, exhaustive-deps = warn) untouched.
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/purity': 'off',
      'react-hooks/refs': 'off',
      'react-hooks/immutability': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/use-memo': 'off',
      'react-hooks/static-components': 'off',
      'react-hooks/component-hook-factories': 'off',
      'react-hooks/set-state-in-render': 'off',
      'react-hooks/error-boundaries': 'off',
      'react-hooks/globals': 'off',
      'react-hooks/gating': 'off',
      'react-hooks/config': 'off',
    },
  },
  {
    // Help content modules intentionally co-locate a content component with
    // the article-metadata object that registers it. These are data modules,
    // not fast-refreshable route components, so the Vite HMR constraint does
    // not apply.
    files: ['src/content/help/**/*.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
