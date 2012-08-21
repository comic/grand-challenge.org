function mlabIsTrue(stringValue) {
  return ["true", "yes", "1", "on"].indexOf(stringValue.toLowerCase()) >= 0;
}


// check if a path starts with $(MLAB_Xxxx_Yyyy):
var mlabPackageVarRegExp = /^\$\(MLAB_\w+_\w+\)/i

function mlabTranslatePath(path) {
  // returns a list of matches:
  var matches = mlabPackageVarRegExp.exec(path);
  if (matches) {
    var match = matches[0]
    path = path.substring(match.length);
    match = match.substring(7, match.length-1).replace("_", "/");
    path = gApp.urlToMLABRoot() + '/' + match + path;
  }
  return path;
}


function mlabTrimConsoleMessage(message) {
  var s = message.replace(/\n/g, ",  ");
  if (s.length > 120) {
    s = s.substr(0, 120) + "   [...]";
  }
  return s;
}


function mlabGetMDLChild(tree, childName) {
  if (tree.children) {
    for (var i=0; i<tree.children.length; i++) {
      var c = tree.children[i];
      if (c.name == childName) {
        return c;
      }
    }
  }
  return null;
}

function mlabGetMDLChildValue(tree, childName, defaultValue) {
  if (tree.children) {
    for (var i=0; i<tree.children.length; i++) {
      var c = tree.children[i];
      if (c.name == childName) {
        return c.value;
      }
    }
  }
  return defaultValue;
}

function mlabGetMDLChildren(tree, childName) {
  result = []
  if (tree.children) {
    for (var i=0; i<tree.children.length; i++) {
      var c = tree.children[i];
      if (c.name == childName) {
        result.push(c);
      }
    }
  }
  return result;
}

function mlabGetStackTrace(depth) {
  var stackTrace = [];
  try {
    getStackTrace_undefined += 1;
  } catch(e) {
    if (e.stack) {
      var lines = e.stack.split('\n');
      for (var i=0; i<lines.length; i++) {
        stackTrace.push(lines[i]);
      }
      // remove this stack
      stackTrace.shift();
    }
  }
  if (stackTrace.length == 0) {
    var caller = arguments.callee.caller;
    while (caller) {
      var callerString = caller.toString();
      var name = callerString.substring(callerString.indexOf("function") + 8, callerString.indexOf('')) || 'anonymous';
      stackTrace.push(name);
      caller = caller.caller;
    }
  }
  
  // remove the specified depth from the callstack
  for (var i=0; i<depth; i++) { stackTrace.shift(); }
  return stackTrace.join("\n");
}


function mlabThrowException(message) {
  var s = message + "\n" + mlabGetStackTrace(depth=2);
  throw s;
}


function mlabEncodeBase64(s) {
  var abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var r = '';
  var length = s.length/3;
  if (s.length > length*3) { length += 1; }  
  for (var i=0; i<length; i++) {
    var idx = i*3;
    var c0 = s.charCodeAt(idx++);
    if (idx < s.length) {
      var c1 = s.charCodeAt(idx++);
      if (idx < s.length) {
        var c2 = s.charCodeAt(idx);
        var b = (c0<<16) | (c1<<8) | c2;
        r += abc.charAt((b>>18) & 63) + abc.charAt((b>>12) & 63) + abc.charAt((b>>6) & 63) + abc.charAt(b & 63);
      } else {
        var b = (c0<<16) | (c1<<8);
        r += abc.charAt((b>>18) & 63) + abc.charAt((b>>12) & 63) + abc.charAt((b>>6) & 63) + '=';
      }
    } else {
      var b = (c0<<16);
      r += abc.charAt((b>>18) & 63) + abc.charAt((b>>12) & 63) + '==';
    }
  }
  return r;
}


function mlabDecodeBase64(s) {
  var abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var r = '';
  var length = s.length/4;  
  for (var i=0; i<length; i++) {
    var idx = i*4;
    var c0 = s.charAt(idx++);
    var c1 = s.charAt(idx++);
    var c2 = s.charAt(idx++);
    var c3 = s.charAt(idx);
    
    if (c2 == "=") {
      var b = (abc.indexOf(c0)<<18) | (abc.indexOf(c1)<<12);
      r += String.fromCharCode((b>>16) & 255);
    } else if (c3 == "=") {
      var b = (abc.indexOf(c0)<<18) | (abc.indexOf(c1)<<12) | (abc.indexOf(c2)<<6);
      r += String.fromCharCode((b>>16) & 255, (b>>8) & 255);
    } else {
      var b = (abc.indexOf(c0)<<18) | (abc.indexOf(c1)<<12) | (abc.indexOf(c2)<<6) | abc.indexOf(c3);
      r += String.fromCharCode((b>>16) & 255, (b>>8) & 255, b & 255);
    }
  }
  return r;
}


function mlabGetComputedBackgroundColor(element) {
  if (window.getComputedStyle) {
    return window.getComputedStyle(element).getPropertyValue("background-color");
  } else if (element.currentStyle) {
    return element.currentStyle.backgroundColor;
  }
  return null;
}


function mlabGetComputedColor(element) {
  if (window.getComputedStyle) {
    return window.getComputedStyle(element).getPropertyValue("color");
  } else if (element.currentStyle) {
    return element.currentStyle.color;
  }
  return null;
}


function mlabAddCSSClass(element, classname) {
  var cls = element.getAttribute("class");
  if (!cls || cls.length == 0) {
    cls = classname;
  } else {
    cls += " " + classname;
  }
  element.setAttribute("class", cls);
}


function mlabRemoveCSSClass(element, classname) {
  var cls = element.getAttribute("class");
  cls = cls.replace(classname, '');
  cls = cls.replace(/^\s+/, '').replace(/\s+$/, '');
  element.setAttribute("class", cls);
}


// reimplementation of C++ function MLABUtils::getAutomaticFieldTitle()
function mlabGetAutomaticFieldTitle(fieldName, splitUppercase) {
  if (fieldName.length == 0) { return fieldName; }
  
  var i = fieldName.indexOf(".");
  if (i<0) { 
    i=0; 
  } else {
    i++;
  }
  if (fieldName.length <= i) { return fieldName; }
  
  var s = fieldName.charAt(i).toUpperCase();
  var lower = false;
  for (++i; i<fieldName.length; i++) {
    var ref = fieldName.charAt(i);
    var isUpperCase = (ref == ref.toUpperCase());
    if (isUpperCase && lower) {
      s += ' ';
    }
    lower = !isUpperCase;
    if (ref == '_') {
      s += ' ';
    } else {
      if (splitUppercase) {
        s += ref;
      } else {
        s += ref.toLowerCase();
      }
    }
  }
  
  return s;
}
