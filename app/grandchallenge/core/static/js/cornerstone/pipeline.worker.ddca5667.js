(function() {
  "use strict";
  function getDefaultExportFromCjs(x) {
    return x && x.__esModule && Object.prototype.hasOwnProperty.call(x, "default") ? x["default"] : x;
  }
  var register = { exports: {} };
  var _createClass$1 = function() {
    function defineProperties(target, props) {
      for (var i = 0; i < props.length; i++) {
        var descriptor = props[i];
        descriptor.enumerable = descriptor.enumerable || false;
        descriptor.configurable = true;
        if ("value" in descriptor)
          descriptor.writable = true;
        Object.defineProperty(target, descriptor.key, descriptor);
      }
    }
    return function(Constructor, protoProps, staticProps) {
      if (protoProps)
        defineProperties(Constructor.prototype, protoProps);
      if (staticProps)
        defineProperties(Constructor, staticProps);
      return Constructor;
    };
  }();
  function _classCallCheck$1(instance, Constructor) {
    if (!(instance instanceof Constructor)) {
      throw new TypeError("Cannot call a class as a function");
    }
  }
  var TinyEmitter$1 = function() {
    function TinyEmitter2() {
      _classCallCheck$1(this, TinyEmitter2);
      Object.defineProperty(this, "__listeners", {
        value: {},
        enumerable: false,
        writable: false
      });
    }
    _createClass$1(TinyEmitter2, [{
      key: "emit",
      value: function emit(eventName) {
        if (!this.__listeners[eventName])
          return this;
        for (var _len = arguments.length, args = Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
          args[_key - 1] = arguments[_key];
        }
        var _iteratorNormalCompletion = true;
        var _didIteratorError = false;
        var _iteratorError = void 0;
        try {
          for (var _iterator = this.__listeners[eventName][Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
            var handler = _step.value;
            handler.apply(void 0, args);
          }
        } catch (err) {
          _didIteratorError = true;
          _iteratorError = err;
        } finally {
          try {
            if (!_iteratorNormalCompletion && _iterator.return) {
              _iterator.return();
            }
          } finally {
            if (_didIteratorError) {
              throw _iteratorError;
            }
          }
        }
        return this;
      }
    }, {
      key: "once",
      value: function once(eventName, handler) {
        var _this = this;
        var once2 = function once3() {
          _this.off(eventName, once3);
          handler.apply(void 0, arguments);
        };
        return this.on(eventName, once2);
      }
    }, {
      key: "on",
      value: function on(eventName, handler) {
        if (!this.__listeners[eventName])
          this.__listeners[eventName] = [];
        this.__listeners[eventName].push(handler);
        return this;
      }
    }, {
      key: "off",
      value: function off(eventName, handler) {
        if (handler)
          this.__listeners[eventName] = this.__listeners[eventName].filter(function(h) {
            return h !== handler;
          });
        else
          this.__listeners[eventName] = [];
        return this;
      }
    }]);
    return TinyEmitter2;
  }();
  var tinyEmitter = TinyEmitter$1;
  var _createClass = function() {
    function defineProperties(target, props) {
      for (var i = 0; i < props.length; i++) {
        var descriptor = props[i];
        descriptor.enumerable = descriptor.enumerable || false;
        descriptor.configurable = true;
        if ("value" in descriptor)
          descriptor.writable = true;
        Object.defineProperty(target, descriptor.key, descriptor);
      }
    }
    return function(Constructor, protoProps, staticProps) {
      if (protoProps)
        defineProperties(Constructor.prototype, protoProps);
      if (staticProps)
        defineProperties(Constructor, staticProps);
      return Constructor;
    };
  }();
  var _get = function get(object, property, receiver) {
    if (object === null)
      object = Function.prototype;
    var desc = Object.getOwnPropertyDescriptor(object, property);
    if (desc === void 0) {
      var parent = Object.getPrototypeOf(object);
      if (parent === null) {
        return void 0;
      } else {
        return get(parent, property, receiver);
      }
    } else if ("value" in desc) {
      return desc.value;
    } else {
      var getter = desc.get;
      if (getter === void 0) {
        return void 0;
      }
      return getter.call(receiver);
    }
  };
  var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function(obj) {
    return typeof obj;
  } : function(obj) {
    return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj;
  };
  function _toConsumableArray(arr) {
    if (Array.isArray(arr)) {
      for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) {
        arr2[i] = arr[i];
      }
      return arr2;
    } else {
      return Array.from(arr);
    }
  }
  function _classCallCheck(instance, Constructor) {
    if (!(instance instanceof Constructor)) {
      throw new TypeError("Cannot call a class as a function");
    }
  }
  function _possibleConstructorReturn(self2, call) {
    if (!self2) {
      throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
    }
    return call && (typeof call === "object" || typeof call === "function") ? call : self2;
  }
  function _inherits(subClass, superClass) {
    if (typeof superClass !== "function" && superClass !== null) {
      throw new TypeError("Super expression must either be null or a function, not " + typeof superClass);
    }
    subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } });
    if (superClass)
      Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass;
  }
  function _defineProperty(obj, key, value) {
    if (key in obj) {
      Object.defineProperty(obj, key, { value, enumerable: true, configurable: true, writable: true });
    } else {
      obj[key] = value;
    }
    return obj;
  }
  var TinyEmitter = tinyEmitter;
  var MESSAGE_RESULT = 0;
  var MESSAGE_EVENT = 1;
  var RESULT_ERROR = 0;
  var RESULT_SUCCESS = 1;
  var DEFAULT_HANDLER = "main";
  var isPromise = function isPromise2(o) {
    return (typeof o === "undefined" ? "undefined" : _typeof(o)) === "object" && o !== null && typeof o.then === "function" && typeof o.catch === "function";
  };
  function RegisterPromise(fn) {
    var handlers = _defineProperty({}, DEFAULT_HANDLER, fn);
    var sendPostMessage = self.postMessage.bind(self);
    var server = new (function(_TinyEmitter) {
      _inherits(WorkerRegister, _TinyEmitter);
      function WorkerRegister() {
        _classCallCheck(this, WorkerRegister);
        return _possibleConstructorReturn(this, (WorkerRegister.__proto__ || Object.getPrototypeOf(WorkerRegister)).apply(this, arguments));
      }
      _createClass(WorkerRegister, [{
        key: "emit",
        value: function emit(eventName) {
          for (var _len = arguments.length, args = Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
            args[_key - 1] = arguments[_key];
          }
          if (args.length == 1 && args[0] instanceof TransferableResponse) {
            sendPostMessage({ eventName, args }, args[0].transferable);
          } else {
            sendPostMessage({ eventName, args });
          }
          return this;
        }
      }, {
        key: "emitLocally",
        value: function emitLocally(eventName) {
          var _get2;
          for (var _len2 = arguments.length, args = Array(_len2 > 1 ? _len2 - 1 : 0), _key2 = 1; _key2 < _len2; _key2++) {
            args[_key2 - 1] = arguments[_key2];
          }
          (_get2 = _get(WorkerRegister.prototype.__proto__ || Object.getPrototypeOf(WorkerRegister.prototype), "emit", this)).call.apply(_get2, [this, eventName].concat(args));
        }
      }, {
        key: "operation",
        value: function operation(name, handler) {
          handlers[name] = handler;
          return this;
        }
      }]);
      return WorkerRegister;
    }(TinyEmitter))();
    var run = function run2(messageId, payload, handlerName) {
      var onSuccess = function onSuccess2(result2) {
        if (result2 && result2 instanceof TransferableResponse) {
          sendResult(messageId, RESULT_SUCCESS, result2.payload, result2.transferable);
        } else {
          sendResult(messageId, RESULT_SUCCESS, result2);
        }
      };
      var onError = function onError2(e) {
        sendResult(messageId, RESULT_ERROR, {
          message: e.message,
          stack: e.stack
        });
      };
      try {
        var result = runFn(messageId, payload, handlerName);
        if (isPromise(result)) {
          result.then(onSuccess).catch(onError);
        } else {
          onSuccess(result);
        }
      } catch (e) {
        onError(e);
      }
    };
    var runFn = function runFn2(messageId, payload, handlerName) {
      var handler = handlers[handlerName || DEFAULT_HANDLER];
      if (!handler)
        throw new Error("Not found handler for this request");
      return handler(payload, sendEvent.bind(null, messageId));
    };
    var sendResult = function sendResult2(messageId, success, payload) {
      var transferable = arguments.length > 3 && arguments[3] !== void 0 ? arguments[3] : [];
      sendPostMessage([MESSAGE_RESULT, messageId, success, payload], transferable);
    };
    var sendEvent = function sendEvent2(messageId, eventName, payload) {
      if (!eventName)
        throw new Error("eventName is required");
      if (typeof eventName !== "string")
        throw new Error("eventName should be string");
      sendPostMessage([MESSAGE_EVENT, messageId, eventName, payload]);
    };
    self.addEventListener("message", function(_ref) {
      var data2 = _ref.data;
      if (Array.isArray(data2)) {
        run.apply(void 0, _toConsumableArray(data2));
      } else if (data2 && data2.eventName) {
        server.emitLocally.apply(server, [data2.eventName].concat(_toConsumableArray(data2.args)));
      }
    });
    return server;
  }
  var TransferableResponse = function TransferableResponse2(payload, transferable) {
    _classCallCheck(this, TransferableResponse2);
    this.payload = payload;
    this.transferable = transferable;
  };
  register.exports = RegisterPromise;
  register.exports.TransferableResponse = TransferableResponse;
  var axios$3 = { exports: {} };
  var axios$2 = { exports: {} };
  var bind$2 = function bind2(fn, thisArg) {
    return function wrap() {
      var args = new Array(arguments.length);
      for (var i = 0; i < args.length; i++) {
        args[i] = arguments[i];
      }
      return fn.apply(thisArg, args);
    };
  };
  var bind$1 = bind$2;
  var toString = Object.prototype.toString;
  function isArray(val) {
    return toString.call(val) === "[object Array]";
  }
  function isUndefined(val) {
    return typeof val === "undefined";
  }
  function isBuffer(val) {
    return val !== null && !isUndefined(val) && val.constructor !== null && !isUndefined(val.constructor) && typeof val.constructor.isBuffer === "function" && val.constructor.isBuffer(val);
  }
  function isArrayBuffer(val) {
    return toString.call(val) === "[object ArrayBuffer]";
  }
  function isFormData(val) {
    return typeof FormData !== "undefined" && val instanceof FormData;
  }
  function isArrayBufferView(val) {
    var result;
    if (typeof ArrayBuffer !== "undefined" && ArrayBuffer.isView) {
      result = ArrayBuffer.isView(val);
    } else {
      result = val && val.buffer && val.buffer instanceof ArrayBuffer;
    }
    return result;
  }
  function isString(val) {
    return typeof val === "string";
  }
  function isNumber(val) {
    return typeof val === "number";
  }
  function isObject(val) {
    return val !== null && typeof val === "object";
  }
  function isPlainObject(val) {
    if (toString.call(val) !== "[object Object]") {
      return false;
    }
    var prototype = Object.getPrototypeOf(val);
    return prototype === null || prototype === Object.prototype;
  }
  function isDate(val) {
    return toString.call(val) === "[object Date]";
  }
  function isFile(val) {
    return toString.call(val) === "[object File]";
  }
  function isBlob(val) {
    return toString.call(val) === "[object Blob]";
  }
  function isFunction(val) {
    return toString.call(val) === "[object Function]";
  }
  function isStream(val) {
    return isObject(val) && isFunction(val.pipe);
  }
  function isURLSearchParams(val) {
    return typeof URLSearchParams !== "undefined" && val instanceof URLSearchParams;
  }
  function trim(str) {
    return str.trim ? str.trim() : str.replace(/^\s+|\s+$/g, "");
  }
  function isStandardBrowserEnv() {
    if (typeof navigator !== "undefined" && (navigator.product === "ReactNative" || navigator.product === "NativeScript" || navigator.product === "NS")) {
      return false;
    }
    return typeof window !== "undefined" && typeof document !== "undefined";
  }
  function forEach(obj, fn) {
    if (obj === null || typeof obj === "undefined") {
      return;
    }
    if (typeof obj !== "object") {
      obj = [obj];
    }
    if (isArray(obj)) {
      for (var i = 0, l = obj.length; i < l; i++) {
        fn.call(null, obj[i], i, obj);
      }
    } else {
      for (var key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          fn.call(null, obj[key], key, obj);
        }
      }
    }
  }
  function merge() {
    var result = {};
    function assignValue(val, key) {
      if (isPlainObject(result[key]) && isPlainObject(val)) {
        result[key] = merge(result[key], val);
      } else if (isPlainObject(val)) {
        result[key] = merge({}, val);
      } else if (isArray(val)) {
        result[key] = val.slice();
      } else {
        result[key] = val;
      }
    }
    for (var i = 0, l = arguments.length; i < l; i++) {
      forEach(arguments[i], assignValue);
    }
    return result;
  }
  function extend(a, b, thisArg) {
    forEach(b, function assignValue(val, key) {
      if (thisArg && typeof val === "function") {
        a[key] = bind$1(val, thisArg);
      } else {
        a[key] = val;
      }
    });
    return a;
  }
  function stripBOM(content) {
    if (content.charCodeAt(0) === 65279) {
      content = content.slice(1);
    }
    return content;
  }
  var utils$8 = {
    isArray,
    isArrayBuffer,
    isBuffer,
    isFormData,
    isArrayBufferView,
    isString,
    isNumber,
    isObject,
    isPlainObject,
    isUndefined,
    isDate,
    isFile,
    isBlob,
    isFunction,
    isStream,
    isURLSearchParams,
    isStandardBrowserEnv,
    forEach,
    merge,
    extend,
    trim,
    stripBOM
  };
  var utils$7 = utils$8;
  function encode(val) {
    return encodeURIComponent(val).replace(/%3A/gi, ":").replace(/%24/g, "$").replace(/%2C/gi, ",").replace(/%20/g, "+").replace(/%5B/gi, "[").replace(/%5D/gi, "]");
  }
  var buildURL$1 = function buildURL2(url, params, paramsSerializer) {
    if (!params) {
      return url;
    }
    var serializedParams;
    if (paramsSerializer) {
      serializedParams = paramsSerializer(params);
    } else if (utils$7.isURLSearchParams(params)) {
      serializedParams = params.toString();
    } else {
      var parts = [];
      utils$7.forEach(params, function serialize(val, key) {
        if (val === null || typeof val === "undefined") {
          return;
        }
        if (utils$7.isArray(val)) {
          key = key + "[]";
        } else {
          val = [val];
        }
        utils$7.forEach(val, function parseValue(v) {
          if (utils$7.isDate(v)) {
            v = v.toISOString();
          } else if (utils$7.isObject(v)) {
            v = JSON.stringify(v);
          }
          parts.push(encode(key) + "=" + encode(v));
        });
      });
      serializedParams = parts.join("&");
    }
    if (serializedParams) {
      var hashmarkIndex = url.indexOf("#");
      if (hashmarkIndex !== -1) {
        url = url.slice(0, hashmarkIndex);
      }
      url += (url.indexOf("?") === -1 ? "?" : "&") + serializedParams;
    }
    return url;
  };
  var utils$6 = utils$8;
  function InterceptorManager$1() {
    this.handlers = [];
  }
  InterceptorManager$1.prototype.use = function use(fulfilled, rejected, options) {
    this.handlers.push({
      fulfilled,
      rejected,
      synchronous: options ? options.synchronous : false,
      runWhen: options ? options.runWhen : null
    });
    return this.handlers.length - 1;
  };
  InterceptorManager$1.prototype.eject = function eject(id) {
    if (this.handlers[id]) {
      this.handlers[id] = null;
    }
  };
  InterceptorManager$1.prototype.forEach = function forEach2(fn) {
    utils$6.forEach(this.handlers, function forEachHandler(h) {
      if (h !== null) {
        fn(h);
      }
    });
  };
  var InterceptorManager_1 = InterceptorManager$1;
  var utils$5 = utils$8;
  var normalizeHeaderName = function normalizeHeaderName2(headers, normalizedName) {
    utils$5.forEach(headers, function processHeader(value, name) {
      if (name !== normalizedName && name.toUpperCase() === normalizedName.toUpperCase()) {
        headers[normalizedName] = value;
        delete headers[name];
      }
    });
  };
  var enhanceError = function enhanceError2(error, config, code, request, response) {
    error.config = config;
    if (code) {
      error.code = code;
    }
    error.request = request;
    error.response = response;
    error.isAxiosError = true;
    error.toJSON = function toJSON() {
      return {
        message: this.message,
        name: this.name,
        description: this.description,
        number: this.number,
        fileName: this.fileName,
        lineNumber: this.lineNumber,
        columnNumber: this.columnNumber,
        stack: this.stack,
        config: this.config,
        code: this.code,
        status: this.response && this.response.status ? this.response.status : null
      };
    };
    return error;
  };
  var createError;
  var hasRequiredCreateError;
  function requireCreateError() {
    if (hasRequiredCreateError)
      return createError;
    hasRequiredCreateError = 1;
    var enhanceError$1 = enhanceError;
    createError = function createError2(message, config, code, request, response) {
      var error = new Error(message);
      return enhanceError$1(error, config, code, request, response);
    };
    return createError;
  }
  var settle;
  var hasRequiredSettle;
  function requireSettle() {
    if (hasRequiredSettle)
      return settle;
    hasRequiredSettle = 1;
    var createError2 = requireCreateError();
    settle = function settle2(resolve, reject, response) {
      var validateStatus = response.config.validateStatus;
      if (!response.status || !validateStatus || validateStatus(response.status)) {
        resolve(response);
      } else {
        reject(createError2(
          "Request failed with status code " + response.status,
          response.config,
          null,
          response.request,
          response
        ));
      }
    };
    return settle;
  }
  var cookies;
  var hasRequiredCookies;
  function requireCookies() {
    if (hasRequiredCookies)
      return cookies;
    hasRequiredCookies = 1;
    var utils2 = utils$8;
    cookies = utils2.isStandardBrowserEnv() ? function standardBrowserEnv() {
      return {
        write: function write(name, value, expires, path, domain, secure) {
          var cookie = [];
          cookie.push(name + "=" + encodeURIComponent(value));
          if (utils2.isNumber(expires)) {
            cookie.push("expires=" + new Date(expires).toGMTString());
          }
          if (utils2.isString(path)) {
            cookie.push("path=" + path);
          }
          if (utils2.isString(domain)) {
            cookie.push("domain=" + domain);
          }
          if (secure === true) {
            cookie.push("secure");
          }
          document.cookie = cookie.join("; ");
        },
        read: function read(name) {
          var match = document.cookie.match(new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"));
          return match ? decodeURIComponent(match[3]) : null;
        },
        remove: function remove(name) {
          this.write(name, "", Date.now() - 864e5);
        }
      };
    }() : function nonStandardBrowserEnv() {
      return {
        write: function write() {
        },
        read: function read() {
          return null;
        },
        remove: function remove() {
        }
      };
    }();
    return cookies;
  }
  var isAbsoluteURL;
  var hasRequiredIsAbsoluteURL;
  function requireIsAbsoluteURL() {
    if (hasRequiredIsAbsoluteURL)
      return isAbsoluteURL;
    hasRequiredIsAbsoluteURL = 1;
    isAbsoluteURL = function isAbsoluteURL2(url) {
      return /^([a-z][a-z\d\+\-\.]*:)?\/\//i.test(url);
    };
    return isAbsoluteURL;
  }
  var combineURLs;
  var hasRequiredCombineURLs;
  function requireCombineURLs() {
    if (hasRequiredCombineURLs)
      return combineURLs;
    hasRequiredCombineURLs = 1;
    combineURLs = function combineURLs2(baseURL, relativeURL) {
      return relativeURL ? baseURL.replace(/\/+$/, "") + "/" + relativeURL.replace(/^\/+/, "") : baseURL;
    };
    return combineURLs;
  }
  var buildFullPath;
  var hasRequiredBuildFullPath;
  function requireBuildFullPath() {
    if (hasRequiredBuildFullPath)
      return buildFullPath;
    hasRequiredBuildFullPath = 1;
    var isAbsoluteURL2 = requireIsAbsoluteURL();
    var combineURLs2 = requireCombineURLs();
    buildFullPath = function buildFullPath2(baseURL, requestedURL) {
      if (baseURL && !isAbsoluteURL2(requestedURL)) {
        return combineURLs2(baseURL, requestedURL);
      }
      return requestedURL;
    };
    return buildFullPath;
  }
  var parseHeaders;
  var hasRequiredParseHeaders;
  function requireParseHeaders() {
    if (hasRequiredParseHeaders)
      return parseHeaders;
    hasRequiredParseHeaders = 1;
    var utils2 = utils$8;
    var ignoreDuplicateOf = [
      "age",
      "authorization",
      "content-length",
      "content-type",
      "etag",
      "expires",
      "from",
      "host",
      "if-modified-since",
      "if-unmodified-since",
      "last-modified",
      "location",
      "max-forwards",
      "proxy-authorization",
      "referer",
      "retry-after",
      "user-agent"
    ];
    parseHeaders = function parseHeaders2(headers) {
      var parsed = {};
      var key;
      var val;
      var i;
      if (!headers) {
        return parsed;
      }
      utils2.forEach(headers.split("\n"), function parser(line) {
        i = line.indexOf(":");
        key = utils2.trim(line.substr(0, i)).toLowerCase();
        val = utils2.trim(line.substr(i + 1));
        if (key) {
          if (parsed[key] && ignoreDuplicateOf.indexOf(key) >= 0) {
            return;
          }
          if (key === "set-cookie") {
            parsed[key] = (parsed[key] ? parsed[key] : []).concat([val]);
          } else {
            parsed[key] = parsed[key] ? parsed[key] + ", " + val : val;
          }
        }
      });
      return parsed;
    };
    return parseHeaders;
  }
  var isURLSameOrigin;
  var hasRequiredIsURLSameOrigin;
  function requireIsURLSameOrigin() {
    if (hasRequiredIsURLSameOrigin)
      return isURLSameOrigin;
    hasRequiredIsURLSameOrigin = 1;
    var utils2 = utils$8;
    isURLSameOrigin = utils2.isStandardBrowserEnv() ? function standardBrowserEnv() {
      var msie = /(msie|trident)/i.test(navigator.userAgent);
      var urlParsingNode = document.createElement("a");
      var originURL;
      function resolveURL(url) {
        var href = url;
        if (msie) {
          urlParsingNode.setAttribute("href", href);
          href = urlParsingNode.href;
        }
        urlParsingNode.setAttribute("href", href);
        return {
          href: urlParsingNode.href,
          protocol: urlParsingNode.protocol ? urlParsingNode.protocol.replace(/:$/, "") : "",
          host: urlParsingNode.host,
          search: urlParsingNode.search ? urlParsingNode.search.replace(/^\?/, "") : "",
          hash: urlParsingNode.hash ? urlParsingNode.hash.replace(/^#/, "") : "",
          hostname: urlParsingNode.hostname,
          port: urlParsingNode.port,
          pathname: urlParsingNode.pathname.charAt(0) === "/" ? urlParsingNode.pathname : "/" + urlParsingNode.pathname
        };
      }
      originURL = resolveURL(window.location.href);
      return function isURLSameOrigin2(requestURL) {
        var parsed = utils2.isString(requestURL) ? resolveURL(requestURL) : requestURL;
        return parsed.protocol === originURL.protocol && parsed.host === originURL.host;
      };
    }() : function nonStandardBrowserEnv() {
      return function isURLSameOrigin2() {
        return true;
      };
    }();
    return isURLSameOrigin;
  }
  var Cancel_1;
  var hasRequiredCancel;
  function requireCancel() {
    if (hasRequiredCancel)
      return Cancel_1;
    hasRequiredCancel = 1;
    function Cancel2(message) {
      this.message = message;
    }
    Cancel2.prototype.toString = function toString2() {
      return "Cancel" + (this.message ? ": " + this.message : "");
    };
    Cancel2.prototype.__CANCEL__ = true;
    Cancel_1 = Cancel2;
    return Cancel_1;
  }
  var xhr;
  var hasRequiredXhr;
  function requireXhr() {
    if (hasRequiredXhr)
      return xhr;
    hasRequiredXhr = 1;
    var utils2 = utils$8;
    var settle2 = requireSettle();
    var cookies2 = requireCookies();
    var buildURL2 = buildURL$1;
    var buildFullPath2 = requireBuildFullPath();
    var parseHeaders2 = requireParseHeaders();
    var isURLSameOrigin2 = requireIsURLSameOrigin();
    var createError2 = requireCreateError();
    var defaults2 = requireDefaults();
    var Cancel2 = requireCancel();
    xhr = function xhrAdapter(config) {
      return new Promise(function dispatchXhrRequest(resolve, reject) {
        var requestData = config.data;
        var requestHeaders = config.headers;
        var responseType = config.responseType;
        var onCanceled;
        function done() {
          if (config.cancelToken) {
            config.cancelToken.unsubscribe(onCanceled);
          }
          if (config.signal) {
            config.signal.removeEventListener("abort", onCanceled);
          }
        }
        if (utils2.isFormData(requestData)) {
          delete requestHeaders["Content-Type"];
        }
        var request = new XMLHttpRequest();
        if (config.auth) {
          var username = config.auth.username || "";
          var password = config.auth.password ? unescape(encodeURIComponent(config.auth.password)) : "";
          requestHeaders.Authorization = "Basic " + btoa(username + ":" + password);
        }
        var fullPath = buildFullPath2(config.baseURL, config.url);
        request.open(config.method.toUpperCase(), buildURL2(fullPath, config.params, config.paramsSerializer), true);
        request.timeout = config.timeout;
        function onloadend() {
          if (!request) {
            return;
          }
          var responseHeaders = "getAllResponseHeaders" in request ? parseHeaders2(request.getAllResponseHeaders()) : null;
          var responseData = !responseType || responseType === "text" || responseType === "json" ? request.responseText : request.response;
          var response = {
            data: responseData,
            status: request.status,
            statusText: request.statusText,
            headers: responseHeaders,
            config,
            request
          };
          settle2(function _resolve(value) {
            resolve(value);
            done();
          }, function _reject(err) {
            reject(err);
            done();
          }, response);
          request = null;
        }
        if ("onloadend" in request) {
          request.onloadend = onloadend;
        } else {
          request.onreadystatechange = function handleLoad() {
            if (!request || request.readyState !== 4) {
              return;
            }
            if (request.status === 0 && !(request.responseURL && request.responseURL.indexOf("file:") === 0)) {
              return;
            }
            setTimeout(onloadend);
          };
        }
        request.onabort = function handleAbort() {
          if (!request) {
            return;
          }
          reject(createError2("Request aborted", config, "ECONNABORTED", request));
          request = null;
        };
        request.onerror = function handleError() {
          reject(createError2("Network Error", config, null, request));
          request = null;
        };
        request.ontimeout = function handleTimeout() {
          var timeoutErrorMessage = config.timeout ? "timeout of " + config.timeout + "ms exceeded" : "timeout exceeded";
          var transitional = config.transitional || defaults2.transitional;
          if (config.timeoutErrorMessage) {
            timeoutErrorMessage = config.timeoutErrorMessage;
          }
          reject(createError2(
            timeoutErrorMessage,
            config,
            transitional.clarifyTimeoutError ? "ETIMEDOUT" : "ECONNABORTED",
            request
          ));
          request = null;
        };
        if (utils2.isStandardBrowserEnv()) {
          var xsrfValue = (config.withCredentials || isURLSameOrigin2(fullPath)) && config.xsrfCookieName ? cookies2.read(config.xsrfCookieName) : void 0;
          if (xsrfValue) {
            requestHeaders[config.xsrfHeaderName] = xsrfValue;
          }
        }
        if ("setRequestHeader" in request) {
          utils2.forEach(requestHeaders, function setRequestHeader(val, key) {
            if (typeof requestData === "undefined" && key.toLowerCase() === "content-type") {
              delete requestHeaders[key];
            } else {
              request.setRequestHeader(key, val);
            }
          });
        }
        if (!utils2.isUndefined(config.withCredentials)) {
          request.withCredentials = !!config.withCredentials;
        }
        if (responseType && responseType !== "json") {
          request.responseType = config.responseType;
        }
        if (typeof config.onDownloadProgress === "function") {
          request.addEventListener("progress", config.onDownloadProgress);
        }
        if (typeof config.onUploadProgress === "function" && request.upload) {
          request.upload.addEventListener("progress", config.onUploadProgress);
        }
        if (config.cancelToken || config.signal) {
          onCanceled = function(cancel) {
            if (!request) {
              return;
            }
            reject(!cancel || cancel && cancel.type ? new Cancel2("canceled") : cancel);
            request.abort();
            request = null;
          };
          config.cancelToken && config.cancelToken.subscribe(onCanceled);
          if (config.signal) {
            config.signal.aborted ? onCanceled() : config.signal.addEventListener("abort", onCanceled);
          }
        }
        if (!requestData) {
          requestData = null;
        }
        request.send(requestData);
      });
    };
    return xhr;
  }
  var defaults_1;
  var hasRequiredDefaults;
  function requireDefaults() {
    if (hasRequiredDefaults)
      return defaults_1;
    hasRequiredDefaults = 1;
    var utils2 = utils$8;
    var normalizeHeaderName$1 = normalizeHeaderName;
    var enhanceError$1 = enhanceError;
    var DEFAULT_CONTENT_TYPE = {
      "Content-Type": "application/x-www-form-urlencoded"
    };
    function setContentTypeIfUnset(headers, value) {
      if (!utils2.isUndefined(headers) && utils2.isUndefined(headers["Content-Type"])) {
        headers["Content-Type"] = value;
      }
    }
    function getDefaultAdapter() {
      var adapter;
      if (typeof XMLHttpRequest !== "undefined") {
        adapter = requireXhr();
      } else if (typeof process !== "undefined" && Object.prototype.toString.call(process) === "[object process]") {
        adapter = requireXhr();
      }
      return adapter;
    }
    function stringifySafely(rawValue, parser, encoder2) {
      if (utils2.isString(rawValue)) {
        try {
          (parser || JSON.parse)(rawValue);
          return utils2.trim(rawValue);
        } catch (e) {
          if (e.name !== "SyntaxError") {
            throw e;
          }
        }
      }
      return (encoder2 || JSON.stringify)(rawValue);
    }
    var defaults2 = {
      transitional: {
        silentJSONParsing: true,
        forcedJSONParsing: true,
        clarifyTimeoutError: false
      },
      adapter: getDefaultAdapter(),
      transformRequest: [function transformRequest(data2, headers) {
        normalizeHeaderName$1(headers, "Accept");
        normalizeHeaderName$1(headers, "Content-Type");
        if (utils2.isFormData(data2) || utils2.isArrayBuffer(data2) || utils2.isBuffer(data2) || utils2.isStream(data2) || utils2.isFile(data2) || utils2.isBlob(data2)) {
          return data2;
        }
        if (utils2.isArrayBufferView(data2)) {
          return data2.buffer;
        }
        if (utils2.isURLSearchParams(data2)) {
          setContentTypeIfUnset(headers, "application/x-www-form-urlencoded;charset=utf-8");
          return data2.toString();
        }
        if (utils2.isObject(data2) || headers && headers["Content-Type"] === "application/json") {
          setContentTypeIfUnset(headers, "application/json");
          return stringifySafely(data2);
        }
        return data2;
      }],
      transformResponse: [function transformResponse(data2) {
        var transitional = this.transitional || defaults2.transitional;
        var silentJSONParsing = transitional && transitional.silentJSONParsing;
        var forcedJSONParsing = transitional && transitional.forcedJSONParsing;
        var strictJSONParsing = !silentJSONParsing && this.responseType === "json";
        if (strictJSONParsing || forcedJSONParsing && utils2.isString(data2) && data2.length) {
          try {
            return JSON.parse(data2);
          } catch (e) {
            if (strictJSONParsing) {
              if (e.name === "SyntaxError") {
                throw enhanceError$1(e, this, "E_JSON_PARSE");
              }
              throw e;
            }
          }
        }
        return data2;
      }],
      timeout: 0,
      xsrfCookieName: "XSRF-TOKEN",
      xsrfHeaderName: "X-XSRF-TOKEN",
      maxContentLength: -1,
      maxBodyLength: -1,
      validateStatus: function validateStatus(status) {
        return status >= 200 && status < 300;
      },
      headers: {
        common: {
          "Accept": "application/json, text/plain, */*"
        }
      }
    };
    utils2.forEach(["delete", "get", "head"], function forEachMethodNoData(method) {
      defaults2.headers[method] = {};
    });
    utils2.forEach(["post", "put", "patch"], function forEachMethodWithData(method) {
      defaults2.headers[method] = utils2.merge(DEFAULT_CONTENT_TYPE);
    });
    defaults_1 = defaults2;
    return defaults_1;
  }
  var utils$4 = utils$8;
  var defaults$2 = requireDefaults();
  var transformData$1 = function transformData2(data2, headers, fns) {
    var context = this || defaults$2;
    utils$4.forEach(fns, function transform(fn) {
      data2 = fn.call(context, data2, headers);
    });
    return data2;
  };
  var isCancel$1;
  var hasRequiredIsCancel;
  function requireIsCancel() {
    if (hasRequiredIsCancel)
      return isCancel$1;
    hasRequiredIsCancel = 1;
    isCancel$1 = function isCancel2(value) {
      return !!(value && value.__CANCEL__);
    };
    return isCancel$1;
  }
  var utils$3 = utils$8;
  var transformData = transformData$1;
  var isCancel = requireIsCancel();
  var defaults$1 = requireDefaults();
  var Cancel = requireCancel();
  function throwIfCancellationRequested(config) {
    if (config.cancelToken) {
      config.cancelToken.throwIfRequested();
    }
    if (config.signal && config.signal.aborted) {
      throw new Cancel("canceled");
    }
  }
  var dispatchRequest$1 = function dispatchRequest2(config) {
    throwIfCancellationRequested(config);
    config.headers = config.headers || {};
    config.data = transformData.call(
      config,
      config.data,
      config.headers,
      config.transformRequest
    );
    config.headers = utils$3.merge(
      config.headers.common || {},
      config.headers[config.method] || {},
      config.headers
    );
    utils$3.forEach(
      ["delete", "get", "head", "post", "put", "patch", "common"],
      function cleanHeaderConfig(method) {
        delete config.headers[method];
      }
    );
    var adapter = config.adapter || defaults$1.adapter;
    return adapter(config).then(function onAdapterResolution(response) {
      throwIfCancellationRequested(config);
      response.data = transformData.call(
        config,
        response.data,
        response.headers,
        config.transformResponse
      );
      return response;
    }, function onAdapterRejection(reason) {
      if (!isCancel(reason)) {
        throwIfCancellationRequested(config);
        if (reason && reason.response) {
          reason.response.data = transformData.call(
            config,
            reason.response.data,
            reason.response.headers,
            config.transformResponse
          );
        }
      }
      return Promise.reject(reason);
    });
  };
  var utils$2 = utils$8;
  var mergeConfig$2 = function mergeConfig2(config1, config2) {
    config2 = config2 || {};
    var config = {};
    function getMergedValue(target, source) {
      if (utils$2.isPlainObject(target) && utils$2.isPlainObject(source)) {
        return utils$2.merge(target, source);
      } else if (utils$2.isPlainObject(source)) {
        return utils$2.merge({}, source);
      } else if (utils$2.isArray(source)) {
        return source.slice();
      }
      return source;
    }
    function mergeDeepProperties(prop) {
      if (!utils$2.isUndefined(config2[prop])) {
        return getMergedValue(config1[prop], config2[prop]);
      } else if (!utils$2.isUndefined(config1[prop])) {
        return getMergedValue(void 0, config1[prop]);
      }
    }
    function valueFromConfig2(prop) {
      if (!utils$2.isUndefined(config2[prop])) {
        return getMergedValue(void 0, config2[prop]);
      }
    }
    function defaultToConfig2(prop) {
      if (!utils$2.isUndefined(config2[prop])) {
        return getMergedValue(void 0, config2[prop]);
      } else if (!utils$2.isUndefined(config1[prop])) {
        return getMergedValue(void 0, config1[prop]);
      }
    }
    function mergeDirectKeys(prop) {
      if (prop in config2) {
        return getMergedValue(config1[prop], config2[prop]);
      } else if (prop in config1) {
        return getMergedValue(void 0, config1[prop]);
      }
    }
    var mergeMap = {
      "url": valueFromConfig2,
      "method": valueFromConfig2,
      "data": valueFromConfig2,
      "baseURL": defaultToConfig2,
      "transformRequest": defaultToConfig2,
      "transformResponse": defaultToConfig2,
      "paramsSerializer": defaultToConfig2,
      "timeout": defaultToConfig2,
      "timeoutMessage": defaultToConfig2,
      "withCredentials": defaultToConfig2,
      "adapter": defaultToConfig2,
      "responseType": defaultToConfig2,
      "xsrfCookieName": defaultToConfig2,
      "xsrfHeaderName": defaultToConfig2,
      "onUploadProgress": defaultToConfig2,
      "onDownloadProgress": defaultToConfig2,
      "decompress": defaultToConfig2,
      "maxContentLength": defaultToConfig2,
      "maxBodyLength": defaultToConfig2,
      "transport": defaultToConfig2,
      "httpAgent": defaultToConfig2,
      "httpsAgent": defaultToConfig2,
      "cancelToken": defaultToConfig2,
      "socketPath": defaultToConfig2,
      "responseEncoding": defaultToConfig2,
      "validateStatus": mergeDirectKeys
    };
    utils$2.forEach(Object.keys(config1).concat(Object.keys(config2)), function computeConfigValue(prop) {
      var merge2 = mergeMap[prop] || mergeDeepProperties;
      var configValue = merge2(prop);
      utils$2.isUndefined(configValue) && merge2 !== mergeDirectKeys || (config[prop] = configValue);
    });
    return config;
  };
  var data;
  var hasRequiredData;
  function requireData() {
    if (hasRequiredData)
      return data;
    hasRequiredData = 1;
    data = {
      "version": "0.23.0"
    };
    return data;
  }
  var VERSION = requireData().version;
  var validators$1 = {};
  ["object", "boolean", "number", "function", "string", "symbol"].forEach(function(type, i) {
    validators$1[type] = function validator2(thing) {
      return typeof thing === type || "a" + (i < 1 ? "n " : " ") + type;
    };
  });
  var deprecatedWarnings = {};
  validators$1.transitional = function transitional(validator2, version, message) {
    function formatMessage(opt, desc) {
      return "[Axios v" + VERSION + "] Transitional option '" + opt + "'" + desc + (message ? ". " + message : "");
    }
    return function(value, opt, opts) {
      if (validator2 === false) {
        throw new Error(formatMessage(opt, " has been removed" + (version ? " in " + version : "")));
      }
      if (version && !deprecatedWarnings[opt]) {
        deprecatedWarnings[opt] = true;
        console.warn(
          formatMessage(
            opt,
            " has been deprecated since v" + version + " and will be removed in the near future"
          )
        );
      }
      return validator2 ? validator2(value, opt, opts) : true;
    };
  };
  function assertOptions(options, schema, allowUnknown) {
    if (typeof options !== "object") {
      throw new TypeError("options must be an object");
    }
    var keys = Object.keys(options);
    var i = keys.length;
    while (i-- > 0) {
      var opt = keys[i];
      var validator2 = schema[opt];
      if (validator2) {
        var value = options[opt];
        var result = value === void 0 || validator2(value, opt, options);
        if (result !== true) {
          throw new TypeError("option " + opt + " must be " + result);
        }
        continue;
      }
      if (allowUnknown !== true) {
        throw Error("Unknown option " + opt);
      }
    }
  }
  var validator$1 = {
    assertOptions,
    validators: validators$1
  };
  var utils$1 = utils$8;
  var buildURL = buildURL$1;
  var InterceptorManager = InterceptorManager_1;
  var dispatchRequest = dispatchRequest$1;
  var mergeConfig$1 = mergeConfig$2;
  var validator = validator$1;
  var validators = validator.validators;
  function Axios$1(instanceConfig) {
    this.defaults = instanceConfig;
    this.interceptors = {
      request: new InterceptorManager(),
      response: new InterceptorManager()
    };
  }
  Axios$1.prototype.request = function request(config) {
    if (typeof config === "string") {
      config = arguments[1] || {};
      config.url = arguments[0];
    } else {
      config = config || {};
    }
    config = mergeConfig$1(this.defaults, config);
    if (config.method) {
      config.method = config.method.toLowerCase();
    } else if (this.defaults.method) {
      config.method = this.defaults.method.toLowerCase();
    } else {
      config.method = "get";
    }
    var transitional = config.transitional;
    if (transitional !== void 0) {
      validator.assertOptions(transitional, {
        silentJSONParsing: validators.transitional(validators.boolean),
        forcedJSONParsing: validators.transitional(validators.boolean),
        clarifyTimeoutError: validators.transitional(validators.boolean)
      }, false);
    }
    var requestInterceptorChain = [];
    var synchronousRequestInterceptors = true;
    this.interceptors.request.forEach(function unshiftRequestInterceptors(interceptor) {
      if (typeof interceptor.runWhen === "function" && interceptor.runWhen(config) === false) {
        return;
      }
      synchronousRequestInterceptors = synchronousRequestInterceptors && interceptor.synchronous;
      requestInterceptorChain.unshift(interceptor.fulfilled, interceptor.rejected);
    });
    var responseInterceptorChain = [];
    this.interceptors.response.forEach(function pushResponseInterceptors(interceptor) {
      responseInterceptorChain.push(interceptor.fulfilled, interceptor.rejected);
    });
    var promise;
    if (!synchronousRequestInterceptors) {
      var chain = [dispatchRequest, void 0];
      Array.prototype.unshift.apply(chain, requestInterceptorChain);
      chain = chain.concat(responseInterceptorChain);
      promise = Promise.resolve(config);
      while (chain.length) {
        promise = promise.then(chain.shift(), chain.shift());
      }
      return promise;
    }
    var newConfig = config;
    while (requestInterceptorChain.length) {
      var onFulfilled = requestInterceptorChain.shift();
      var onRejected = requestInterceptorChain.shift();
      try {
        newConfig = onFulfilled(newConfig);
      } catch (error) {
        onRejected(error);
        break;
      }
    }
    try {
      promise = dispatchRequest(newConfig);
    } catch (error) {
      return Promise.reject(error);
    }
    while (responseInterceptorChain.length) {
      promise = promise.then(responseInterceptorChain.shift(), responseInterceptorChain.shift());
    }
    return promise;
  };
  Axios$1.prototype.getUri = function getUri(config) {
    config = mergeConfig$1(this.defaults, config);
    return buildURL(config.url, config.params, config.paramsSerializer).replace(/^\?/, "");
  };
  utils$1.forEach(["delete", "get", "head", "options"], function forEachMethodNoData(method) {
    Axios$1.prototype[method] = function(url, config) {
      return this.request(mergeConfig$1(config || {}, {
        method,
        url,
        data: (config || {}).data
      }));
    };
  });
  utils$1.forEach(["post", "put", "patch"], function forEachMethodWithData(method) {
    Axios$1.prototype[method] = function(url, data2, config) {
      return this.request(mergeConfig$1(config || {}, {
        method,
        url,
        data: data2
      }));
    };
  });
  var Axios_1 = Axios$1;
  var CancelToken_1;
  var hasRequiredCancelToken;
  function requireCancelToken() {
    if (hasRequiredCancelToken)
      return CancelToken_1;
    hasRequiredCancelToken = 1;
    var Cancel2 = requireCancel();
    function CancelToken(executor) {
      if (typeof executor !== "function") {
        throw new TypeError("executor must be a function.");
      }
      var resolvePromise;
      this.promise = new Promise(function promiseExecutor(resolve) {
        resolvePromise = resolve;
      });
      var token = this;
      this.promise.then(function(cancel) {
        if (!token._listeners)
          return;
        var i;
        var l = token._listeners.length;
        for (i = 0; i < l; i++) {
          token._listeners[i](cancel);
        }
        token._listeners = null;
      });
      this.promise.then = function(onfulfilled) {
        var _resolve;
        var promise = new Promise(function(resolve) {
          token.subscribe(resolve);
          _resolve = resolve;
        }).then(onfulfilled);
        promise.cancel = function reject() {
          token.unsubscribe(_resolve);
        };
        return promise;
      };
      executor(function cancel(message) {
        if (token.reason) {
          return;
        }
        token.reason = new Cancel2(message);
        resolvePromise(token.reason);
      });
    }
    CancelToken.prototype.throwIfRequested = function throwIfRequested() {
      if (this.reason) {
        throw this.reason;
      }
    };
    CancelToken.prototype.subscribe = function subscribe(listener) {
      if (this.reason) {
        listener(this.reason);
        return;
      }
      if (this._listeners) {
        this._listeners.push(listener);
      } else {
        this._listeners = [listener];
      }
    };
    CancelToken.prototype.unsubscribe = function unsubscribe(listener) {
      if (!this._listeners) {
        return;
      }
      var index = this._listeners.indexOf(listener);
      if (index !== -1) {
        this._listeners.splice(index, 1);
      }
    };
    CancelToken.source = function source() {
      var cancel;
      var token = new CancelToken(function executor(c) {
        cancel = c;
      });
      return {
        token,
        cancel
      };
    };
    CancelToken_1 = CancelToken;
    return CancelToken_1;
  }
  var spread;
  var hasRequiredSpread;
  function requireSpread() {
    if (hasRequiredSpread)
      return spread;
    hasRequiredSpread = 1;
    spread = function spread2(callback) {
      return function wrap(arr) {
        return callback.apply(null, arr);
      };
    };
    return spread;
  }
  var isAxiosError;
  var hasRequiredIsAxiosError;
  function requireIsAxiosError() {
    if (hasRequiredIsAxiosError)
      return isAxiosError;
    hasRequiredIsAxiosError = 1;
    isAxiosError = function isAxiosError2(payload) {
      return typeof payload === "object" && payload.isAxiosError === true;
    };
    return isAxiosError;
  }
  var utils = utils$8;
  var bind = bind$2;
  var Axios = Axios_1;
  var mergeConfig = mergeConfig$2;
  var defaults = requireDefaults();
  function createInstance(defaultConfig) {
    var context = new Axios(defaultConfig);
    var instance = bind(Axios.prototype.request, context);
    utils.extend(instance, Axios.prototype, context);
    utils.extend(instance, context);
    instance.create = function create(instanceConfig) {
      return createInstance(mergeConfig(defaultConfig, instanceConfig));
    };
    return instance;
  }
  var axios$1 = createInstance(defaults);
  axios$1.Axios = Axios;
  axios$1.Cancel = requireCancel();
  axios$1.CancelToken = requireCancelToken();
  axios$1.isCancel = requireIsCancel();
  axios$1.VERSION = requireData().version;
  axios$1.all = function all(promises) {
    return Promise.all(promises);
  };
  axios$1.spread = requireSpread();
  axios$1.isAxiosError = requireIsAxiosError();
  axios$2.exports = axios$1;
  axios$2.exports.default = axios$1;
  (function(module) {
    module.exports = axios$2.exports;
  })(axios$3);
  var axios = /* @__PURE__ */ getDefaultExportFromCjs(axios$3.exports);
  async function loadEmscriptenModuleWebWorker(moduleRelativePathOrURL, baseUrl) {
    let modulePrefix = null;
    if (typeof moduleRelativePathOrURL !== "string") {
      modulePrefix = moduleRelativePathOrURL.href;
    } else if (moduleRelativePathOrURL.startsWith("http")) {
      modulePrefix = moduleRelativePathOrURL;
    } else {
      modulePrefix = `${baseUrl}/${moduleRelativePathOrURL}`;
    }
    if (modulePrefix.endsWith(".js")) {
      modulePrefix = modulePrefix.substring(0, modulePrefix.length - 3);
    }
    if (modulePrefix.endsWith(".wasm")) {
      modulePrefix = modulePrefix.substring(0, modulePrefix.length - 5);
    }
    const wasmBinaryPath = `${modulePrefix}.wasm`;
    const response = await axios.get(wasmBinaryPath, { responseType: "arraybuffer" });
    const wasmBinary = response.data;
    const modulePath = `${modulePrefix}.umd.js`;
    importScripts(modulePath);
    const moduleBaseName = modulePrefix.replace(/.*\//, "");
    const wrapperModule = self[moduleBaseName];
    const emscriptenModule = wrapperModule({ wasmBinary });
    return emscriptenModule;
  }
  const pipelineToModule = /* @__PURE__ */ new Map();
  async function loadPipelineModule(pipelinePath, baseUrl) {
    let moduleRelativePathOrURL = pipelinePath;
    let pipeline = pipelinePath;
    let pipelineModule = null;
    if (typeof pipelinePath !== "string") {
      moduleRelativePathOrURL = new URL(pipelinePath.href);
      pipeline = moduleRelativePathOrURL.href;
    }
    if (pipelineToModule.has(pipeline)) {
      pipelineModule = pipelineToModule.get(pipeline);
    } else {
      pipelineToModule.set(pipeline, await loadEmscriptenModuleWebWorker(moduleRelativePathOrURL, baseUrl));
      pipelineModule = pipelineToModule.get(pipeline);
    }
    return pipelineModule;
  }
  const mimeToIO$1 = /* @__PURE__ */ new Map([
    ["image/jpeg", "JPEGImageIO"],
    ["image/png", "PNGImageIO"],
    ["image/tiff", "TIFFImageIO"],
    ["image/x-ms-bmp", "BMPImageIO"],
    ["image/x-bmp", "BMPImageIO"],
    ["image/bmp", "BMPImageIO"],
    ["application/dicom", "GDCMImageIO"]
  ]);
  const extensionToIO$1 = /* @__PURE__ */ new Map([
    ["bmp", "BMPImageIO"],
    ["BMP", "BMPImageIO"],
    ["dcm", "GDCMImageIO"],
    ["DCM", "GDCMImageIO"],
    ["gipl", "GiplImageIO"],
    ["gipl.gz", "GiplImageIO"],
    ["hdf5", "HDF5ImageIO"],
    ["jpg", "JPEGImageIO"],
    ["JPG", "JPEGImageIO"],
    ["jpeg", "JPEGImageIO"],
    ["JPEG", "JPEGImageIO"],
    ["iwi", "WASMImageIO"],
    ["iwi.cbor", "WASMImageIO"],
    ["iwi.cbor.zstd", "WASMZstdImageIO"],
    ["lsm", "LSMImageIO"],
    ["mnc", "MINCImageIO"],
    ["MNC", "MINCImageIO"],
    ["mnc.gz", "MINCImageIO"],
    ["MNC.GZ", "MINCImageIO"],
    ["mnc2", "MINCImageIO"],
    ["MNC2", "MINCImageIO"],
    ["mgh", "MGHImageIO"],
    ["mgz", "MGHImageIO"],
    ["mgh.gz", "MGHImageIO"],
    ["mha", "MetaImageIO"],
    ["mhd", "MetaImageIO"],
    ["mrc", "MRCImageIO"],
    ["nia", "NiftiImageIO"],
    ["nii", "NiftiImageIO"],
    ["nii.gz", "NiftiImageIO"],
    ["hdr", "NiftiImageIO"],
    ["nrrd", "NrrdImageIO"],
    ["NRRD", "NrrdImageIO"],
    ["nhdr", "NrrdImageIO"],
    ["NHDR", "NrrdImageIO"],
    ["png", "PNGImageIO"],
    ["PNG", "PNGImageIO"],
    ["pic", "BioRadImageIO"],
    ["PIC", "BioRadImageIO"],
    ["tif", "TIFFImageIO"],
    ["TIF", "TIFFImageIO"],
    ["tiff", "TIFFImageIO"],
    ["TIFF", "TIFFImageIO"],
    ["vtk", "VTKImageIO"],
    ["VTK", "VTKImageIO"],
    ["isq", "ScancoImageIO"],
    ["ISQ", "ScancoImageIO"],
    ["fdf", "FDFImageIO"],
    ["FDF", "FDFImageIO"]
  ]);
  function getFileExtension(filePath) {
    let extension = filePath.slice((filePath.lastIndexOf(".") - 1 >>> 0) + 2);
    if (extension.toLowerCase() === "gz") {
      const index = filePath.slice(0, -3).lastIndexOf(".");
      extension = filePath.slice((index - 1 >>> 0) + 2);
    } else if (extension.toLowerCase() === "cbor") {
      const index = filePath.slice(0, -5).lastIndexOf(".");
      extension = filePath.slice((index - 1 >>> 0) + 2);
    } else if (extension.toLowerCase() === "zstd") {
      const index = filePath.slice(0, -10).lastIndexOf(".");
      extension = filePath.slice((index - 1 >>> 0) + 2);
    } else if (extension.toLowerCase() === "zip") {
      const index = filePath.slice(0, -4).lastIndexOf(".");
      extension = filePath.slice((index - 1 >>> 0) + 2);
    }
    return extension;
  }
  const ImageIOIndex = ["PNGImageIO", "MetaImageIO", "TIFFImageIO", "NiftiImageIO", "JPEGImageIO", "NrrdImageIO", "VTKImageIO", "BMPImageIO", "HDF5ImageIO", "MINCImageIO", "MRCImageIO", "LSMImageIO", "MGHImageIO", "BioRadImageIO", "GiplImageIO", "GEAdwImageIO", "GE4ImageIO", "GE5ImageIO", "GDCMImageIO", "ScancoImageIO", "FDFImageIO", "WASMImageIO", "WASMZstdImageIO"];
  const InterfaceTypes = {
    TextFile: "InterfaceTextFile",
    BinaryFile: "InterfaceBinaryFile",
    TextStream: "InterfaceTextStream",
    BinaryStream: "InterfaceBinaryStream",
    Image: "InterfaceImage",
    Mesh: "InterfaceMesh",
    PolyData: "InterfacePolyData"
  };
  const IOTypes = {
    Text: "Text",
    Binary: "Binary",
    Image: "Image",
    Mesh: "Mesh"
  };
  const IntTypes = {
    Int8: "int8",
    UInt8: "uint8",
    Int16: "int16",
    UInt16: "uint16",
    Int32: "int32",
    UInt32: "uint32",
    Int64: "int64",
    UInt64: "uint64",
    SizeValueType: "uint64",
    IdentifierType: "uint64",
    IndexValueType: "int64",
    OffsetValueType: "int64"
  };
  var IntTypes$1 = IntTypes;
  const FloatTypes = {
    Float32: "float32",
    Float64: "float64",
    SpacePrecisionType: "float64"
  };
  var FloatTypes$1 = FloatTypes;
  function bufferToTypedArray(wasmType, buffer) {
    let typedArray = null;
    switch (wasmType) {
      case IntTypes$1.UInt8: {
        typedArray = new Uint8Array(buffer);
        break;
      }
      case IntTypes$1.Int8: {
        typedArray = new Int8Array(buffer);
        break;
      }
      case IntTypes$1.UInt16: {
        typedArray = new Uint16Array(buffer);
        break;
      }
      case IntTypes$1.Int16: {
        typedArray = new Int16Array(buffer);
        break;
      }
      case IntTypes$1.UInt32: {
        typedArray = new Uint32Array(buffer);
        break;
      }
      case IntTypes$1.Int32: {
        typedArray = new Int32Array(buffer);
        break;
      }
      case IntTypes$1.UInt64: {
        if (typeof globalThis.BigUint64Array === "function") {
          typedArray = new BigUint64Array(buffer);
        } else {
          typedArray = new Uint8Array(buffer);
        }
        break;
      }
      case IntTypes$1.Int64: {
        if (typeof globalThis.BigInt64Array === "function") {
          typedArray = new BigInt64Array(buffer);
        } else {
          typedArray = new Uint8Array(buffer);
        }
        break;
      }
      case FloatTypes$1.Float32: {
        typedArray = new Float32Array(buffer);
        break;
      }
      case FloatTypes$1.Float64: {
        typedArray = new Float64Array(buffer);
        break;
      }
      case "null": {
        typedArray = null;
        break;
      }
      case null: {
        typedArray = null;
        break;
      }
      default:
        throw new Error("Type is not supported as a TypedArray");
    }
    return typedArray;
  }
  const haveSharedArrayBuffer$1 = typeof globalThis.SharedArrayBuffer === "function";
  const encoder = new TextEncoder();
  const decoder = new TextDecoder("utf-8");
  function readFileSharedArray(emscriptenModule, path) {
    const opts = { flags: "r", encoding: "binary" };
    const stream = emscriptenModule.fs_open(path, opts.flags);
    const stat = emscriptenModule.fs_stat(path);
    const length = stat.size;
    let arrayBufferData = null;
    if (haveSharedArrayBuffer$1) {
      arrayBufferData = new SharedArrayBuffer(length);
    } else {
      arrayBufferData = new ArrayBuffer(length);
    }
    const array = new Uint8Array(arrayBufferData);
    emscriptenModule.fs_read(stream, array, 0, length, 0);
    emscriptenModule.fs_close(stream);
    return array;
  }
  function memoryUint8SharedArray(emscriptenModule, byteOffset, length) {
    let arrayBufferData = null;
    if (haveSharedArrayBuffer$1) {
      arrayBufferData = new SharedArrayBuffer(length);
    } else {
      arrayBufferData = new ArrayBuffer(length);
    }
    const array = new Uint8Array(arrayBufferData);
    const dataArrayView = new Uint8Array(emscriptenModule.HEAPU8.buffer, byteOffset, length);
    array.set(dataArrayView);
    return array;
  }
  function setPipelineModuleInputArray(emscriptenModule, dataArray, inputIndex, subIndex) {
    let dataPtr = 0;
    if (dataArray !== null) {
      dataPtr = emscriptenModule.ccall("itk_wasm_input_array_alloc", "number", ["number", "number", "number", "number"], [0, inputIndex, subIndex, dataArray.buffer.byteLength]);
      emscriptenModule.HEAPU8.set(new Uint8Array(dataArray.buffer), dataPtr);
    }
    return dataPtr;
  }
  function setPipelineModuleInputJSON(emscriptenModule, dataObject, inputIndex) {
    const dataJSON = JSON.stringify(dataObject);
    const jsonPtr = emscriptenModule.ccall("itk_wasm_input_json_alloc", "number", ["number", "number", "number"], [0, inputIndex, dataJSON.length]);
    emscriptenModule.writeAsciiToMemory(dataJSON, jsonPtr, false);
  }
  function getPipelineModuleOutputArray(emscriptenModule, outputIndex, subIndex, componentType) {
    const dataPtr = emscriptenModule.ccall("itk_wasm_output_array_address", "number", ["number", "number", "number"], [0, outputIndex, subIndex]);
    const dataSize = emscriptenModule.ccall("itk_wasm_output_array_size", "number", ["number", "number", "number"], [0, outputIndex, subIndex]);
    const dataUint8 = memoryUint8SharedArray(emscriptenModule, dataPtr, dataSize);
    const data2 = bufferToTypedArray(componentType, dataUint8.buffer);
    return data2;
  }
  function getPipelineModuleOutputJSON(emscriptenModule, outputIndex) {
    const jsonPtr = emscriptenModule.ccall("itk_wasm_output_json_address", "number", ["number", "number"], [0, outputIndex]);
    const dataJSON = emscriptenModule.AsciiToString(jsonPtr);
    const dataObject = JSON.parse(dataJSON);
    return dataObject;
  }
  function runPipelineEmscripten(pipelineModule, args, outputs, inputs) {
    if (!(inputs == null) && inputs.length > 0) {
      inputs.forEach(function(input, index) {
        switch (input.type) {
          case InterfaceTypes.TextStream: {
            const dataArray = encoder.encode(input.data.data);
            const arrayPtr = setPipelineModuleInputArray(pipelineModule, dataArray, index, 0);
            const dataJSON = { size: dataArray.buffer.byteLength, data: `data:application/vnd.itk.address,0:${arrayPtr}` };
            setPipelineModuleInputJSON(pipelineModule, dataJSON, index);
            break;
          }
          case InterfaceTypes.BinaryStream: {
            const dataArray = input.data.data;
            const arrayPtr = setPipelineModuleInputArray(pipelineModule, dataArray, index, 0);
            const dataJSON = { size: dataArray.buffer.byteLength, data: `data:application/vnd.itk.address,0:${arrayPtr}` };
            setPipelineModuleInputJSON(pipelineModule, dataJSON, index);
            break;
          }
          case InterfaceTypes.TextFile: {
            pipelineModule.fs_writeFile(input.data.path, input.data.data);
            break;
          }
          case InterfaceTypes.BinaryFile: {
            pipelineModule.fs_writeFile(input.data.path, input.data.data);
            break;
          }
          case InterfaceTypes.Image: {
            const image = input.data;
            const dataPtr = setPipelineModuleInputArray(pipelineModule, image.data, index, 0);
            const directionPtr = setPipelineModuleInputArray(pipelineModule, image.direction, index, 1);
            const imageJSON = {
              imageType: image.imageType,
              name: image.name,
              origin: image.origin,
              spacing: image.spacing,
              direction: `data:application/vnd.itk.address,0:${directionPtr}`,
              size: image.size,
              data: `data:application/vnd.itk.address,0:${dataPtr}`
            };
            setPipelineModuleInputJSON(pipelineModule, imageJSON, index);
            break;
          }
          case InterfaceTypes.Mesh: {
            const mesh = input.data;
            const pointsPtr = setPipelineModuleInputArray(pipelineModule, mesh.points, index, 0);
            const cellsPtr = setPipelineModuleInputArray(pipelineModule, mesh.cells, index, 1);
            const pointDataPtr = setPipelineModuleInputArray(pipelineModule, mesh.pointData, index, 2);
            const cellDataPtr = setPipelineModuleInputArray(pipelineModule, mesh.pointData, index, 3);
            const meshJSON = {
              meshType: mesh.meshType,
              name: mesh.name,
              numberOfPoints: mesh.numberOfPoints,
              points: `data:application/vnd.itk.address,0:${pointsPtr}`,
              numberOfCells: mesh.numberOfCells,
              cells: `data:application/vnd.itk.address,0:${cellsPtr}`,
              cellBufferSize: mesh.cellBufferSize,
              numberOfPointPixels: mesh.numberOfPointPixels,
              pointData: `data:application/vnd.itk.address,0:${pointDataPtr}`,
              numberOfCellPixels: mesh.numberOfCellPixels,
              cellData: `data:application/vnd.itk.address,0:${cellDataPtr}`
            };
            setPipelineModuleInputJSON(pipelineModule, meshJSON, index);
            break;
          }
          case InterfaceTypes.PolyData: {
            const polyData = input.data;
            const pointsPtr = setPipelineModuleInputArray(pipelineModule, polyData.points, index, 0);
            const verticesPtr = setPipelineModuleInputArray(pipelineModule, polyData.vertices, index, 1);
            const linesPtr = setPipelineModuleInputArray(pipelineModule, polyData.lines, index, 2);
            const polygonsPtr = setPipelineModuleInputArray(pipelineModule, polyData.polygons, index, 3);
            const triangleStripsPtr = setPipelineModuleInputArray(pipelineModule, polyData.triangleStrips, index, 4);
            const pointDataPtr = setPipelineModuleInputArray(pipelineModule, polyData.pointData, index, 5);
            const cellDataPtr = setPipelineModuleInputArray(pipelineModule, polyData.pointData, index, 6);
            const polyDataJSON = {
              polyDataType: polyData.polyDataType,
              name: polyData.name,
              numberOfPoints: polyData.numberOfPoints,
              points: `data:application/vnd.itk.address,0:${pointsPtr}`,
              verticesBufferSize: polyData.verticesBufferSize,
              vertices: `data:application/vnd.itk.address,0:${verticesPtr}`,
              linesBufferSize: polyData.linesBufferSize,
              lines: `data:application/vnd.itk.address,0:${linesPtr}`,
              polygonsBufferSize: polyData.polygonsBufferSize,
              polygons: `data:application/vnd.itk.address,0:${polygonsPtr}`,
              triangleStripsBufferSize: polyData.triangleStripsBufferSize,
              triangleStrips: `data:application/vnd.itk.address,0:${triangleStripsPtr}`,
              numberOfPointPixels: polyData.numberOfPointPixels,
              pointData: `data:application/vnd.itk.address,0:${pointDataPtr}`,
              numberOfCellPixels: polyData.numberOfCellPixels,
              cellData: `data:application/vnd.itk.address,0:${cellDataPtr}`
            };
            setPipelineModuleInputJSON(pipelineModule, polyDataJSON, index);
            break;
          }
          case IOTypes.Text: {
            pipelineModule.fs_writeFile(input.path, input.data);
            break;
          }
          case IOTypes.Binary: {
            pipelineModule.fs_writeFile(input.path, input.data);
            break;
          }
          case IOTypes.Image: {
            const image = input.data;
            const imageJSON = {
              imageType: image.imageType,
              name: image.name,
              origin: image.origin,
              spacing: image.spacing,
              direction: "data:application/vnd.itk.path,data/direction.raw",
              size: image.size,
              data: "data:application/vnd.itk.path,data/data.raw"
            };
            pipelineModule.fs_mkdirs(`${input.path}/data`);
            pipelineModule.fs_writeFile(`${input.path}/index.json`, JSON.stringify(imageJSON));
            if (image.data === null) {
              throw Error("image.data is null");
            }
            pipelineModule.fs_writeFile(`${input.path}/data/data.raw`, new Uint8Array(image.data.buffer));
            pipelineModule.fs_writeFile(`${input.path}/data/direction.raw`, new Uint8Array(image.direction.buffer));
            break;
          }
          case IOTypes.Mesh: {
            const mesh = input.data;
            const meshJSON = {
              meshType: mesh.meshType,
              name: mesh.name,
              numberOfPoints: mesh.numberOfPoints,
              points: "data:application/vnd.itk.path,data/points.raw",
              numberOfPointPixels: mesh.numberOfPointPixels,
              pointData: "data:application/vnd.itk.path,data/pointData.raw",
              numberOfCells: mesh.numberOfCells,
              cells: "data:application/vnd.itk.path,data/cells.raw",
              numberOfCellPixels: mesh.numberOfCellPixels,
              cellData: "data:application/vnd.itk.path,data/cellData.raw",
              cellBufferSize: mesh.cellBufferSize
            };
            pipelineModule.fs_mkdirs(`${input.path}/data`);
            pipelineModule.fs_writeFile(`${input.path}/index.json`, JSON.stringify(meshJSON));
            if (meshJSON.numberOfPoints > 0) {
              if (mesh.points === null) {
                throw Error("mesh.points is null");
              }
              pipelineModule.fs_writeFile(`${input.path}/data/points.raw`, new Uint8Array(mesh.points.buffer));
            }
            if (meshJSON.numberOfPointPixels > 0) {
              if (mesh.pointData === null) {
                throw Error("mesh.pointData is null");
              }
              pipelineModule.fs_writeFile(`${input.path}/data/pointData.raw`, new Uint8Array(mesh.pointData.buffer));
            }
            if (meshJSON.numberOfCells > 0) {
              if (mesh.cells === null) {
                throw Error("mesh.cells is null");
              }
              pipelineModule.fs_writeFile(`${input.path}/data/cells.raw`, new Uint8Array(mesh.cells.buffer));
            }
            if (meshJSON.numberOfCellPixels > 0) {
              if (mesh.cellData === null) {
                throw Error("mesh.cellData is null");
              }
              pipelineModule.fs_writeFile(`${input.path}/data/cellData.raw`, new Uint8Array(mesh.cellData.buffer));
            }
            break;
          }
          default:
            throw Error("Unsupported input InterfaceType");
        }
      });
    }
    pipelineModule.resetModuleStdout();
    pipelineModule.resetModuleStderr();
    let returnValue = 0;
    try {
      returnValue = pipelineModule.callMain(args);
    } catch (exception) {
      if (typeof exception === "number") {
        console.log("Exception while running pipeline:");
        console.log("stdout:", pipelineModule.getModuleStdout());
        console.error("stderr:", pipelineModule.getModuleStderr());
        if (typeof pipelineModule.getExceptionMessage !== "undefined") {
          console.error("exception:", pipelineModule.getExceptionMessage(exception));
        } else {
          console.error("Build module in Debug mode for exception message information.");
        }
      }
      throw exception;
    }
    const stdout = pipelineModule.getModuleStdout();
    const stderr = pipelineModule.getModuleStderr();
    const populatedOutputs = [];
    if (!(outputs == null) && outputs.length > 0 && returnValue === 0) {
      outputs.forEach(function(output, index) {
        let outputData = null;
        switch (output.type) {
          case InterfaceTypes.TextStream: {
            const dataPtr = pipelineModule.ccall("itk_wasm_output_array_address", "number", ["number", "number", "number"], [0, index, 0]);
            const dataSize = pipelineModule.ccall("itk_wasm_output_array_size", "number", ["number", "number", "number"], [0, index, 0]);
            const dataArrayView = new Uint8Array(pipelineModule.HEAPU8.buffer, dataPtr, dataSize);
            outputData = { data: decoder.decode(dataArrayView) };
            break;
          }
          case InterfaceTypes.BinaryStream: {
            const dataPtr = pipelineModule.ccall("itk_wasm_output_array_address", "number", ["number", "number", "number"], [0, index, 0]);
            const dataSize = pipelineModule.ccall("itk_wasm_output_array_size", "number", ["number", "number", "number"], [0, index, 0]);
            outputData = { data: memoryUint8SharedArray(pipelineModule, dataPtr, dataSize) };
            break;
          }
          case InterfaceTypes.TextFile: {
            outputData = { path: output.data.path, data: pipelineModule.fs_readFile(output.data.path, { encoding: "utf8" }) };
            break;
          }
          case InterfaceTypes.BinaryFile: {
            outputData = { path: output.data.path, data: readFileSharedArray(pipelineModule, output.data.path) };
            break;
          }
          case InterfaceTypes.Image: {
            const image = getPipelineModuleOutputJSON(pipelineModule, index);
            image.data = getPipelineModuleOutputArray(pipelineModule, index, 0, image.imageType.componentType);
            image.direction = getPipelineModuleOutputArray(pipelineModule, index, 1, FloatTypes$1.Float64);
            outputData = image;
            break;
          }
          case InterfaceTypes.Mesh: {
            const mesh = getPipelineModuleOutputJSON(pipelineModule, index);
            if (mesh.numberOfPoints > 0) {
              mesh.points = getPipelineModuleOutputArray(pipelineModule, index, 0, mesh.meshType.pointComponentType);
            } else {
              mesh.points = bufferToTypedArray(mesh.meshType.pointComponentType, new ArrayBuffer(0));
            }
            if (mesh.numberOfCells > 0) {
              mesh.cells = getPipelineModuleOutputArray(pipelineModule, index, 1, mesh.meshType.cellComponentType);
            } else {
              mesh.cells = bufferToTypedArray(mesh.meshType.cellComponentType, new ArrayBuffer(0));
            }
            if (mesh.numberOfPointPixels > 0) {
              mesh.pointData = getPipelineModuleOutputArray(pipelineModule, index, 2, mesh.meshType.pointPixelComponentType);
            } else {
              mesh.pointData = bufferToTypedArray(mesh.meshType.pointPixelComponentType, new ArrayBuffer(0));
            }
            if (mesh.numberOfCellPixels > 0) {
              mesh.cellData = getPipelineModuleOutputArray(pipelineModule, index, 3, mesh.meshType.cellPixelComponentType);
            } else {
              mesh.cellData = bufferToTypedArray(mesh.meshType.cellPixelComponentType, new ArrayBuffer(0));
            }
            outputData = mesh;
            break;
          }
          case InterfaceTypes.PolyData: {
            const polyData = getPipelineModuleOutputJSON(pipelineModule, index);
            if (polyData.numberOfPoints > 0) {
              polyData.points = getPipelineModuleOutputArray(pipelineModule, index, 0, FloatTypes$1.Float32);
            } else {
              polyData.points = new Float32Array();
            }
            if (polyData.verticesBufferSize > 0) {
              polyData.vertices = getPipelineModuleOutputArray(pipelineModule, index, 1, IntTypes$1.UInt32);
            } else {
              polyData.vertices = new Uint32Array();
            }
            if (polyData.linesBufferSize > 0) {
              polyData.lines = getPipelineModuleOutputArray(pipelineModule, index, 2, IntTypes$1.UInt32);
            } else {
              polyData.lines = new Uint32Array();
            }
            if (polyData.polygonsBufferSize > 0) {
              polyData.polygons = getPipelineModuleOutputArray(pipelineModule, index, 3, IntTypes$1.UInt32);
            } else {
              polyData.polygons = new Uint32Array();
            }
            if (polyData.triangleStripsBufferSize > 0) {
              polyData.triangleStrips = getPipelineModuleOutputArray(pipelineModule, index, 4, IntTypes$1.UInt32);
            } else {
              polyData.triangleStrips = new Uint32Array();
            }
            if (polyData.numberOfPointPixels > 0) {
              polyData.pointData = getPipelineModuleOutputArray(pipelineModule, index, 5, polyData.polyDataType.pointPixelComponentType);
            } else {
              polyData.pointData = bufferToTypedArray(polyData.polyDataType.pointPixelComponentType, new ArrayBuffer(0));
            }
            if (polyData.numberOfCellPixels > 0) {
              polyData.cellData = getPipelineModuleOutputArray(pipelineModule, index, 6, polyData.polyDataType.cellPixelComponentType);
            } else {
              polyData.cellData = bufferToTypedArray(polyData.polyDataType.cellPixelComponentType, new ArrayBuffer(0));
            }
            outputData = polyData;
            break;
          }
          case IOTypes.Text: {
            if (typeof output.path === "undefined") {
              throw new Error("output.path not defined");
            }
            outputData = pipelineModule.fs_readFile(output.path, { encoding: "utf8" });
            break;
          }
          case IOTypes.Binary: {
            if (typeof output.path === "undefined") {
              throw new Error("output.path not defined");
            }
            outputData = readFileSharedArray(pipelineModule, output.path);
            break;
          }
          case IOTypes.Image: {
            if (typeof output.path === "undefined") {
              throw new Error("output.path not defined");
            }
            const imageJSON = pipelineModule.fs_readFile(`${output.path}/index.json`, { encoding: "utf8" });
            const image = JSON.parse(imageJSON);
            const dataUint8 = readFileSharedArray(pipelineModule, `${output.path}/data/data.raw`);
            image.data = bufferToTypedArray(image.imageType.componentType, dataUint8.buffer);
            const directionUint8 = readFileSharedArray(pipelineModule, `${output.path}/data/direction.raw`);
            image.direction = bufferToTypedArray(FloatTypes$1.Float64, directionUint8.buffer);
            outputData = image;
            break;
          }
          case IOTypes.Mesh: {
            if (typeof output.path === "undefined") {
              throw new Error("output.path not defined");
            }
            const meshJSON = pipelineModule.fs_readFile(`${output.path}/index.json`, { encoding: "utf8" });
            const mesh = JSON.parse(meshJSON);
            if (mesh.numberOfPoints > 0) {
              const dataUint8Points = readFileSharedArray(pipelineModule, `${output.path}/data/points.raw`);
              mesh.points = bufferToTypedArray(mesh.meshType.pointComponentType, dataUint8Points.buffer);
            } else {
              mesh.points = bufferToTypedArray(mesh.meshType.pointComponentType, new ArrayBuffer(0));
            }
            if (mesh.numberOfPointPixels > 0) {
              const dataUint8PointData = readFileSharedArray(pipelineModule, `${output.path}/data/pointData.raw`);
              mesh.pointData = bufferToTypedArray(mesh.meshType.pointPixelComponentType, dataUint8PointData.buffer);
            } else {
              mesh.pointData = bufferToTypedArray(mesh.meshType.pointPixelComponentType, new ArrayBuffer(0));
            }
            if (mesh.numberOfCells > 0) {
              const dataUint8Cells = readFileSharedArray(pipelineModule, `${output.path}/data/cells.raw`);
              mesh.cells = bufferToTypedArray(mesh.meshType.cellComponentType, dataUint8Cells.buffer);
            } else {
              mesh.cells = bufferToTypedArray(mesh.meshType.cellComponentType, new ArrayBuffer(0));
            }
            if (mesh.numberOfCellPixels > 0) {
              const dataUint8CellData = readFileSharedArray(pipelineModule, `${output.path}/data/cellData.raw`);
              mesh.cellData = bufferToTypedArray(mesh.meshType.cellPixelComponentType, dataUint8CellData.buffer);
            } else {
              mesh.cellData = bufferToTypedArray(mesh.meshType.cellPixelComponentType, new ArrayBuffer(0));
            }
            outputData = mesh;
            break;
          }
          default:
            throw Error("Unsupported output InterfaceType");
        }
        const populatedOutput = {
          type: output.type,
          data: outputData
        };
        populatedOutputs.push(populatedOutput);
      });
    }
    return { returnValue, stdout, stderr, outputs: populatedOutputs };
  }
  var __await$1 = function(v) {
    return this instanceof __await$1 ? (this.v = v, this) : new __await$1(v);
  };
  var __asyncGenerator$1 = function(thisArg, _arguments, generator) {
    if (!Symbol.asyncIterator)
      throw new TypeError("Symbol.asyncIterator is not defined.");
    var g = generator.apply(thisArg, _arguments || []), i, q = [];
    return i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function() {
      return this;
    }, i;
    function verb(n) {
      if (g[n])
        i[n] = function(v) {
          return new Promise(function(a, b) {
            q.push([n, v, a, b]) > 1 || resume(n, v);
          });
        };
    }
    function resume(n, v) {
      try {
        step(g[n](v));
      } catch (e) {
        settle2(q[0][3], e);
      }
    }
    function step(r) {
      r.value instanceof __await$1 ? Promise.resolve(r.value.v).then(fulfill, reject) : settle2(q[0][2], r);
    }
    function fulfill(value) {
      resume("next", value);
    }
    function reject(value) {
      resume("throw", value);
    }
    function settle2(f, v) {
      if (f(v), q.shift(), q.length)
        resume(q[0][0], q[0][1]);
    }
  };
  var __asyncValues$1 = function(o) {
    if (!Symbol.asyncIterator)
      throw new TypeError("Symbol.asyncIterator is not defined.");
    var m = o[Symbol.asyncIterator], i;
    return m ? m.call(o) : (o = typeof __values === "function" ? __values(o) : o[Symbol.iterator](), i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function() {
      return this;
    }, i);
    function verb(n) {
      i[n] = o[n] && function(v) {
        return new Promise(function(resolve, reject) {
          v = o[n](v), settle2(resolve, reject, v.done, v.value);
        });
      };
    }
    function settle2(resolve, reject, d, v) {
      Promise.resolve(v).then(function(v2) {
        resolve({ value: v2, done: d });
      }, reject);
    }
  };
  function availableIOModules$1(input) {
    return __asyncGenerator$1(this, arguments, function* availableIOModules_1() {
      for (let idx = 0; idx < ImageIOIndex.length; idx++) {
        const trialIO = ImageIOIndex[idx] + "ReadImage";
        const ioModule = yield __await$1(loadPipelineModule(trialIO, input.config.imageIOUrl));
        yield yield __await$1(ioModule);
      }
    });
  }
  async function loadImageIOPipelineModule(input, postfix) {
    var e_1, _a;
    if (input.mimeType && mimeToIO$1.has(input.mimeType)) {
      const io = mimeToIO$1.get(input.mimeType) + postfix;
      const ioModule = await loadPipelineModule(io, input.config.imageIOUrl);
      return ioModule;
    }
    const extension = getFileExtension(input.fileName);
    if (extensionToIO$1.has(extension)) {
      const io = extensionToIO$1.get(extension) + postfix;
      const ioModule = await loadPipelineModule(io, input.config.imageIOUrl);
      return ioModule;
    }
    for (let idx = 0; idx < ImageIOIndex.length; ++idx) {
      let idx2 = 0;
      try {
        for (var _b = (e_1 = void 0, __asyncValues$1(availableIOModules$1(input))), _c; _c = await _b.next(), !_c.done; ) {
          const pipelineModule = _c.value;
          try {
            const { returnValue, outputs } = await runPipelineEmscripten(pipelineModule, input.args, input.outputs, input.inputs);
            if (returnValue === 0) {
              return pipelineModule;
            }
          } catch (error) {
          }
          idx2++;
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (_c && !_c.done && (_a = _b.return))
            await _a.call(_b);
        } finally {
          if (e_1)
            throw e_1.error;
        }
      }
    }
    throw Error(`Could not find IO for: ${input.fileName}`);
  }
  const mimeToIO = /* @__PURE__ */ new Map([]);
  const extensionToIO = /* @__PURE__ */ new Map([
    ["vtk", "VTKPolyDataMeshIO"],
    ["VTK", "VTKPolyDataMeshIO"],
    ["byu", "BYUMeshIO"],
    ["BYU", "BYUMeshIO"],
    ["fsa", "FreeSurferAsciiMeshIO"],
    ["FSA", "FreeSurferAsciiMeshIO"],
    ["fsb", "FreeSurferBinaryMeshIO"],
    ["FSB", "FreeSurferBinaryMeshIO"],
    ["obj", "OBJMeshIO"],
    ["OBJ", "OBJMeshIO"],
    ["off", "OFFMeshIO"],
    ["OFF", "OFFMeshIO"],
    ["stl", "STLMeshIO"],
    ["STL", "STLMeshIO"],
    ["swc", "SWCMeshIO"],
    ["SWC", "SWCMeshIO"],
    ["iwm", "WASMMeshIO"],
    ["iwm.cbor", "WASMMeshIO"],
    ["iwm.cbor.zstd", "WASMZstdMeshIO"]
  ]);
  const MeshIOIndex = ["BYUMeshIO", "FreeSurferAsciiMeshIO", "FreeSurferBinaryMeshIO", "OBJMeshIO", "OFFMeshIO", "STLMeshIO", "SWCMeshIO", "VTKPolyDataMeshIO", "WASMMeshIO", "WASMZstdMeshIO"];
  var __await = function(v) {
    return this instanceof __await ? (this.v = v, this) : new __await(v);
  };
  var __asyncGenerator = function(thisArg, _arguments, generator) {
    if (!Symbol.asyncIterator)
      throw new TypeError("Symbol.asyncIterator is not defined.");
    var g = generator.apply(thisArg, _arguments || []), i, q = [];
    return i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function() {
      return this;
    }, i;
    function verb(n) {
      if (g[n])
        i[n] = function(v) {
          return new Promise(function(a, b) {
            q.push([n, v, a, b]) > 1 || resume(n, v);
          });
        };
    }
    function resume(n, v) {
      try {
        step(g[n](v));
      } catch (e) {
        settle2(q[0][3], e);
      }
    }
    function step(r) {
      r.value instanceof __await ? Promise.resolve(r.value.v).then(fulfill, reject) : settle2(q[0][2], r);
    }
    function fulfill(value) {
      resume("next", value);
    }
    function reject(value) {
      resume("throw", value);
    }
    function settle2(f, v) {
      if (f(v), q.shift(), q.length)
        resume(q[0][0], q[0][1]);
    }
  };
  var __asyncValues = function(o) {
    if (!Symbol.asyncIterator)
      throw new TypeError("Symbol.asyncIterator is not defined.");
    var m = o[Symbol.asyncIterator], i;
    return m ? m.call(o) : (o = typeof __values === "function" ? __values(o) : o[Symbol.iterator](), i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function() {
      return this;
    }, i);
    function verb(n) {
      i[n] = o[n] && function(v) {
        return new Promise(function(resolve, reject) {
          v = o[n](v), settle2(resolve, reject, v.done, v.value);
        });
      };
    }
    function settle2(resolve, reject, d, v) {
      Promise.resolve(v).then(function(v2) {
        resolve({ value: v2, done: d });
      }, reject);
    }
  };
  function availableIOModules(input) {
    return __asyncGenerator(this, arguments, function* availableIOModules_1() {
      for (let idx = 0; idx < MeshIOIndex.length; idx++) {
        const trialIO = MeshIOIndex[idx] + "ReadMesh";
        const ioModule = yield __await(loadPipelineModule(trialIO, input.config.meshIOUrl));
        yield yield __await(ioModule);
      }
    });
  }
  async function loadMeshIOPipelineModule(input, postfix) {
    var e_1, _a;
    if (input.mimeType && mimeToIO.has(input.mimeType)) {
      const io = mimeToIO.get(input.mimeType) + postfix;
      const ioModule = await loadPipelineModule(io, input.config.meshIOUrl);
      return ioModule;
    }
    const extension = getFileExtension(input.fileName);
    if (extensionToIO.has(extension)) {
      const io = extensionToIO.get(extension) + postfix;
      const ioModule = await loadPipelineModule(io, input.config.meshIOUrl);
      return ioModule;
    }
    for (let idx = 0; idx < MeshIOIndex.length; ++idx) {
      let idx2 = 0;
      try {
        for (var _b = (e_1 = void 0, __asyncValues(availableIOModules(input))), _c; _c = await _b.next(), !_c.done; ) {
          const pipelineModule = _c.value;
          try {
            const { returnValue, outputs } = await runPipelineEmscripten(pipelineModule, input.args, input.outputs, input.inputs);
            if (returnValue === 0) {
              return pipelineModule;
            }
          } catch (error) {
          }
          idx2++;
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (_c && !_c.done && (_a = _b.return))
            await _a.call(_b);
        } finally {
          if (e_1)
            throw e_1.error;
        }
      }
    }
    throw Error(`Could not find IO for: ${input.fileName}`);
  }
  const haveSharedArrayBuffer = typeof globalThis.SharedArrayBuffer === "function";
  function getTransferable(data2) {
    let result = null;
    if (data2.buffer !== void 0) {
      result = data2.buffer;
    } else if (data2.byteLength !== void 0) {
      result = data2;
    }
    if (!!result && haveSharedArrayBuffer && result instanceof SharedArrayBuffer) {
      return null;
    }
    return result;
  }
  function meshTransferables(mesh) {
    const transferables = [];
    if (mesh.points != null) {
      transferables.push(mesh.points.buffer);
    }
    if (mesh.pointData != null) {
      transferables.push(mesh.pointData.buffer);
    }
    if (mesh.cells != null) {
      transferables.push(mesh.cells.buffer);
    }
    if (mesh.cellData != null) {
      transferables.push(mesh.cellData.buffer);
    }
    return transferables;
  }
  function polyDataTransferables(polyData) {
    const transferables = [];
    if (polyData.points != null) {
      transferables.push(polyData.points.buffer);
    }
    if (polyData.vertices != null) {
      transferables.push(polyData.vertices.buffer);
    }
    if (polyData.lines != null) {
      transferables.push(polyData.lines.buffer);
    }
    if (polyData.polygons != null) {
      transferables.push(polyData.polygons.buffer);
    }
    if (polyData.triangleStrips != null) {
      transferables.push(polyData.triangleStrips.buffer);
    }
    if (polyData.pointData != null) {
      transferables.push(polyData.pointData.buffer);
    }
    if (polyData.cellData != null) {
      transferables.push(polyData.cellData.buffer);
    }
    return transferables;
  }
  async function runPipeline(pipelineModule, args, outputs, inputs) {
    const result = runPipelineEmscripten(pipelineModule, args, outputs, inputs);
    const transferables = [];
    if (result.outputs) {
      result.outputs.forEach(function(output) {
        if (output.type === InterfaceTypes.BinaryStream || output.type === InterfaceTypes.BinaryFile) {
          const binary = output.data;
          const transferable = getTransferable(binary);
          if (transferable) {
            transferables.push(transferable);
          }
        } else if (output.type === InterfaceTypes.Image) {
          const image = output.data;
          let transferable = getTransferable(image.data);
          if (transferable) {
            transferables.push(transferable);
          }
          transferable = getTransferable(image.direction);
          if (transferable) {
            transferables.push(transferable);
          }
        } else if (output.type === InterfaceTypes.Mesh) {
          const mesh = output.data;
          const mt = meshTransferables(mesh);
          transferables.push(...mt);
        } else if (output.type === InterfaceTypes.PolyData) {
          const polyData = output.data;
          const pt = polyDataTransferables(polyData);
          transferables.push(...pt);
        } else if (output.type === IOTypes.Binary) {
          const binary = output.data;
          const transferable = getTransferable(binary);
          if (transferable) {
            transferables.push(transferable);
          }
        } else if (output.type === IOTypes.Image) {
          const image = output.data;
          let transferable = getTransferable(image.data);
          if (transferable) {
            transferables.push(transferable);
          }
          transferable = getTransferable(image.direction);
          if (transferable) {
            transferables.push(transferable);
          }
        } else if (output.type === IOTypes.Mesh) {
          const mesh = output.data;
          if (mesh.points) {
            const transferable = getTransferable(mesh.points);
            if (transferable) {
              transferables.push(transferable);
            }
          }
          if (mesh.pointData) {
            const transferable = getTransferable(mesh.pointData);
            if (transferable) {
              transferables.push(transferable);
            }
          }
          if (mesh.cells) {
            const transferable = getTransferable(mesh.cells);
            if (transferable) {
              transferables.push(transferable);
            }
          }
          if (mesh.cellData) {
            const transferable = getTransferable(mesh.cellData);
            if (transferable) {
              transferables.push(transferable);
            }
          }
        }
      });
    }
    return new register.exports.TransferableResponse(result, transferables);
  }
  register.exports(async function(input) {
    let pipelineModule = null;
    if (input.operation === "runPipeline") {
      pipelineModule = await loadPipelineModule(input.pipelinePath, input.config.pipelinesUrl);
    } else if (input.operation === "readImage") {
      pipelineModule = await loadImageIOPipelineModule(input, "ReadImage");
    } else if (input.operation === "writeImage") {
      pipelineModule = await loadImageIOPipelineModule(input, "WriteImage");
    } else if (input.operation === "readMesh") {
      pipelineModule = await loadMeshIOPipelineModule(input, "ReadMesh");
    } else if (input.operation === "writeMesh") {
      pipelineModule = await loadMeshIOPipelineModule(input, "WriteMesh");
    } else if (input.operation === "meshToPolyData") {
      pipelineModule = await loadPipelineModule("MeshToPolyData", input.config.meshIOUrl);
    } else if (input.operation === "polyDataToMesh") {
      pipelineModule = await loadPipelineModule("PolyDataToMesh", input.config.meshIOUrl);
    } else if (input.operation === "readDICOMImageSeries") {
      pipelineModule = await loadPipelineModule("ReadImageDICOMFileSeries", input.config.imageIOUrl);
    } else if (input.operation === "readDICOMTags") {
      pipelineModule = await loadPipelineModule("ReadDICOMTags", input.config.imageIOUrl);
    } else {
      throw new Error("Unknown worker operation");
    }
    return runPipeline(pipelineModule, input.args, input.outputs, input.inputs);
  });
})();
