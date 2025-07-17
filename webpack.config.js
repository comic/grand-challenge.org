const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const BundleTracker = require('webpack-bundle-tracker');
const webpack = require('webpack');

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
        // Expose jQuery globally on jQuery and $
        test: require.resolve('jquery'),
        loader: 'expose-loader',
        options: {
          exposes: ['$', 'jQuery'],
        },
      },
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
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
      'window.jQuery': 'jquery'
    }),
    new BundleTracker({
      path: path.resolve(__dirname, 'app/grandchallenge/core/static/vendored'),
      filename: 'webpack-stats.json',
      relativePath: true,
    })
  ],

  mode: 'production',
  optimization: {
    splitChunks: false // Keep each package separate
  }
};
