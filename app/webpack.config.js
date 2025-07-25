const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const BundleTracker = require('webpack-bundle-tracker');
const webpack = require('webpack');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');

const isProduction = process.env.NODE_ENV === 'production';

module.exports = {
  entry: {
    'jquery': 'jquery',
    'bootstrap': 'bootstrap',
    'jsoneditor_widget': './grandchallenge/core/javascript/jsoneditor_widget.mjs',
    'sentry': './grandchallenge/core/javascript/sentry.mjs',
    'cards_info_modal': './grandchallenge/core/javascript/cards_info_modal.js',
  },

  output: {
    path: path.resolve(__dirname, 'grandchallenge/core/static/npm_vendored'),
    filename: isProduction ? '[name].js' : '[name]-[contenthash].js',
    publicPath: '',
    clean: true,
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
          filename: isProduction ? 'assets/[name][ext]' : 'assets/[name]-[contenthash][ext]',
        }
      }
    ]
  },

  plugins: [
    new CleanWebpackPlugin(),
    new MiniCssExtractPlugin({
      filename: isProduction ? '[name].css' : '[name]-[contenthash].css'
    }),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
      'window.jQuery': 'jquery',
    }),
    new BundleTracker({
      path: path.resolve(__dirname, 'grandchallenge/core/static/npm_vendored'),
      filename: 'webpack-stats.json',
      relativePath: true,
    })
  ],

  mode: isProduction ? 'production' : 'development',
  devtool: isProduction ? 'source-map' : 'eval-source-map',
  optimization: {
    splitChunks: {
      chunks: 'all',
      minSize: 0,
    },
    runtimeChunk: 'single',
    minimizer: [
      '...', // keep existing minimizers (like Terser for JS)
      new CssMinimizerPlugin(),
    ],
  }
};
