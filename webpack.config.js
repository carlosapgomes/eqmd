const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = {
  entry: {
    main: ["./assets/index.js", "./assets/scss/main.scss"],
  },
  output: {
    filename: "[name]-bundle.js",
    path: path.resolve(__dirname, "./static"),
    clean: true,
  },
  module: {
    rules: [
      {
        test: /\.scss$/,
        use: [
          MiniCssExtractPlugin.loader,
          "css-loader",
          "postcss-loader",
          "sass-loader",
        ],
      },
      {
        test: /\.woff2?$/,
        type: "asset/resource",
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, "css-loader", "postcss-loader"],
      },
    ],
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: "[name].css",
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: "node_modules/bootstrap/dist/js/bootstrap.min.js",
          to: "js/bootstrap.min.js",
        },
        {
          from: "node_modules/@popperjs/core/dist/umd/popper.min.js",
          to: "js/popper.min.js",
        },
      ],
    }),
  ],
  optimization: {
    minimizer: [`...`, new CssMinimizerPlugin()],
  },
  resolve: {
    extensions: [".js", ".scss", ".css"],
  },
};
