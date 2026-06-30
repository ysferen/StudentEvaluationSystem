import { defineConfig, globalIgnores } from "eslint/config";
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default defineConfig([
    globalIgnores([
        "coverage",
        "dist",
        "node_modules",
        "src/shared/api/generated",
        "src/shared/api/model",
    ]),
    ...typescriptEslint.configs["flat/recommended"],
    reactRefresh.configs.vite,
    {
        plugins: { "react-hooks": reactHooks },
        languageOptions: { globals: globals.browser },
        rules: {
            "react-hooks/rules-of-hooks": "error",
            "react-hooks/exhaustive-deps": "warn",
            "react-refresh/only-export-components": "warn",
            "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
            "@typescript-eslint/no-explicit-any": "warn",
            "@typescript-eslint/no-non-null-assertion": "warn",
            "@typescript-eslint/no-empty-function": "error",
        },
    },
    {
        files: ["src/**/__tests__/**", "src/test/**"],
        rules: { "@typescript-eslint/no-empty-function": "off" },
    },
]);
