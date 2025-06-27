const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = {
  entry: {
    main: [
      "./assets/index.js", 
      "./assets/scss/main.scss",
      "./apps/events/static/events/js/timeline.js",
      "./apps/events/static/events/js/accessibility.js"
    ],
    mediafiles: [
      "./apps/mediafiles/static/mediafiles/js/mediafiles.js",
      "./apps/mediafiles/static/mediafiles/css/mediafiles.css"
    ],
    photo: [
      "./apps/mediafiles/static/mediafiles/js/photo.js",
      "./apps/mediafiles/static/mediafiles/css/photo.css"
    ],
    photoseries: [
      "./apps/mediafiles/static/mediafiles/js/photoseries.js",
      "./apps/mediafiles/static/mediafiles/js/image-processing.js",
      "./apps/mediafiles/static/mediafiles/css/photoseries.css"
    ],
    videoclipUpload: [
      "./apps/mediafiles/static/mediafiles/js/videoclip-upload.js",
      "./apps/mediafiles/static/mediafiles/js/compression/phase3-integration.js",
      "./apps/mediafiles/static/mediafiles/js/compression/ui/compression-controls.js",
      "./apps/mediafiles/static/mediafiles/js/compression/ui/medical-context.js",
      "./apps/mediafiles/static/mediafiles/css/videoclip.css"
    ],
    videoclipPlayer: [
      "./apps/mediafiles/static/mediafiles/js/videoclip-player.js"
    ]
  },
  output: {
    filename: "[name]-bundle.js",
    chunkFilename: "[name]-chunk.js",
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
    minimize: true,
    splitChunks: {
      chunks: 'all',
      maxSize: 244000, // 244KB limit per chunk
      cacheGroups: {
        // Heavy image processing libraries - separate chunk
        imageProcessing: {
          test: /[\\/]node_modules[\\/](browser-image-compression|heic2any)[\\/]/,
          name: 'image-processing',
          chunks: 'all',
          priority: 30,
        },
        // Other vendor libraries
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
          priority: 10,
        },
        // FFmpeg.wasm - separate bundle for lazy loading
        ffmpeg: {
          test: /[\\/]node_modules[\\/]@ffmpeg[\\/]/,
          name: 'ffmpeg-wasm',
          chunks: 'async', // Only loaded when imported dynamically
          priority: 35,
          enforce: true
        },
        // Compression-specific modules (excluding ffmpeg)
        compression: {
          test: /[\\/]compression[\\/].*\.js$/,
          name: 'compression-core',
          chunks: 'all',
          priority: 25,
        },
        // Shared mediafiles utilities
        mediafiles: {
          test: /[\\/]apps[\\/]mediafiles[\\/].*\.js$/,
          name: 'mediafiles-common',
          chunks: 'all',
          minChunks: 2,
          priority: 20,
        }
      }
    }
  },
  resolve: {
    extensions: [".js", ".scss", ".css"],
  },
};
