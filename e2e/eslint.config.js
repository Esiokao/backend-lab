// ESLint flat config for the e2e package.
import tseslint from 'typescript-eslint'

export default tseslint.config(
  // Type-aware rules (no-floating-promises) need project info.
  {
    files: ['tests/**/*.ts', 'playwright.config.ts'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname
      }
    },
    plugins: { '@typescript-eslint': tseslint.plugin },
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_' }
      ]
    }
  }
)
