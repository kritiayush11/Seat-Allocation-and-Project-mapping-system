const path = require("path");

module.exports = {
  style: {
    postcss: {
      mode: "file",
    },
  },
  webpack: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      // Fix: resolve react-refresh to local node_modules to avoid
      // "outside of src/" errors from CRA's absolute path injection
      "react-refresh/runtime": path.resolve(
        __dirname,
        "node_modules/react-refresh/runtime.js",
      ),
    },
    configure: (webpackConfig) => {
      // Allow imports from outside src/ directory
      webpackConfig.resolve = webpackConfig.resolve || {};
      webpackConfig.resolve.plugins = (
        webpackConfig.resolve.plugins || []
      ).filter((plugin) => plugin.constructor.name !== "ModuleScopePlugin");
      return webpackConfig;
    },
  },
};
