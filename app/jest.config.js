module.exports = {
    testEnvironment: "jsdom",

    // A list of paths to modules that run some code to configure or set up the testing framework before each test
    setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],

    // The glob patterns Jest uses to detect test files
    testMatch: ["<rootDir>/tests/*/js/*.test.js"],

    transform: {
        "^.+.(js|mjs)$": "babel-jest",
    },
    moduleNameMapper: {
        ".css$": "identity-obj-proxy",
    },
};
