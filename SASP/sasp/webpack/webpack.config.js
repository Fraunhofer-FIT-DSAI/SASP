const path = require('path');
const webpack = require('webpack');

new webpack.ProvidePlugin({
  $: 'jquery',
  jQuery: 'jquery'
});

module.exports = {
    entry: {
        json_parser: './src/json_parser.js',
        select2: './src/select2.js',
    },
    output: {
        filename: '[name].js',
        path: path.resolve('..', 'static/webpack'),
    },
    plugins: [
      new webpack.ProvidePlugin({
        $: 'jquery',
        jQuery: 'jquery'
      })
    ],
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader'
          }
        },
        { 
          test: /.css$/, 
          use: ['style-loader', 'css-loader'] 
        }
      ]
    },
    resolve: {
      extensions: ['.js', '.jsx']
    },
};