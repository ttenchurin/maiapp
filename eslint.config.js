import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        // Глобальные переменные для Node.js
        process: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        module: "readonly",
        require: "readonly",
        Buffer: "readonly",
        console: "readonly",
        exports: "writable",
      },
    },
    rules: {
      "no-unused-vars": ["error", {
        "argsIgnorePattern": "^_",
        "varsIgnorePattern": "^_"
      }]
    }
  }
];
