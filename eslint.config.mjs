import js from "@eslint/js";
import globals from "globals";
import eslintConfigPrettier from "eslint-config-prettier";

export default [
    {
        ignores: ["app/grandchallenge/core/static/vendored/*"],
    },
    {
        languageOptions: {
            globals: {
                ...globals.browser,
                $: "readonly",
                Uppy: "readonly",
                htmx: "readonly",
                machina: "readonly",
                moment: "readonly",
                vegaEmbed: "readonly",
                Sentry: "readonly",
            },
        },
        rules: {
            ...js.configs.recommended.rules,
            "no-useless-assignment": 2,
            "accessor-pairs": 2,
            semi: 2,
            "prefer-const": 2,
            eqeqeq: 2,
        },
    },
    eslintConfigPrettier,
];
