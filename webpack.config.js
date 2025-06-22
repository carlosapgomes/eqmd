const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = {
  entry: {
    main: [
      "./assets/index.js", 
      "./assets/scss/main.scss",
      "./apps/mediafiles/static/mediafiles/js/mediafiles.js",
      "./apps/events/static/events/js/timeline.js",
      "./apps/events/static/events/js/accessibility.js",
      "./apps/mediafiles/static/mediafiles/js/photo.js",
      "./apps/mediafiles/static/mediafiles/css/mediafiles.css",
      "./apps/mediafiles/static/mediafiles/css/photo.css"
    ],
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
          from: "node_modules/easymde/dist/easymde.min.js",
          to: "js/easymde.min.js",
        },
        {
          from: "node_modules/easymde/dist/easymde.min.css",
          to: "css/easymde.min.css",
        },
        {
          from: "node_modules/bootstrap/dist/js/bootstrap.min.js",
          to: "js/bootstrap.min.js",
        },
        {
          from: "node_modules/bootstrap-icons/font/bootstrap-icons.min.css",
          to: "css/bootstrap-icons.min.css",
        },
        {
          from: "node_modules/bootstrap-icons/font/fonts/bootstrap-icons.woff2",
          to: "css/fonts/bootstrap-icons.woff2",
        },
        {
          from: "node_modules/@popperjs/core/dist/umd/popper.min.js",
          to: "js/popper.min.js",
        },
        // Add these new patterns to copy your assets
        {
          from: "assets/images",
          to: "images",
        },
        {
          from: "assets/*.ico",
          to: "[name][ext]",
        },
        {
          from: "assets/*.png",
          to: "[name][ext]",
          noErrorOnMissing: true,
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
