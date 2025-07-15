const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const BundleTracker = require('webpack-bundle-tracker');

module.exports = {
  entry: {
    'jquery': 'jquery',
  },

  output: {
    path: path.resolve(__dirname, 'app/grandchallenge/core/static/vendored'),
    filename: '[name]-[contenthash].js',
    publicPath: '',
    clean: true
  },

  module: {
    rules: [
      {
        test: /\.css$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader'
        ]
      },
      {
        test: /\.(png|jpe?g|gif|svg|woff|woff2|ttf|eot)$/,
        type: 'asset/resource',
        generator: {
          filename: '[name]-[contenthash][ext]',
          outputPath: 'assets/'
        }
      }
    ]
  },

  plugins: [
    // new CleanWebpackPlugin(),
    new MiniCssExtractPlugin({
      filename: '[name]-[contenthash].css'
    }),
    new BundleTracker({
      path: path.resolve(__dirname, 'app'),
      filename: 'webpack-stats.json',
      relativePath: true,
    })
  ],

  mode: 'production',
  optimization: {
    splitChunks: false // Keep each package separate
  }
};
