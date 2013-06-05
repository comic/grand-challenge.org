
window.MLAB = new (function() {
  
  /**
   * 
   */
  function copyOwnProperties(clss, properties, staticProperties) {
    var propertyNames = Object.getOwnPropertyNames(properties)
    for (var i=0; i<propertyNames.length; i++) {
      var property = propertyNames[i]
      clss.prototype[property]= properties[property]
    }
    if (typeof(staticProperties) !== "undefined") {
      var staticPropertyNames = Object.getOwnPropertyNames(staticProperties)
      for (var i=0; i<staticPropertyNames.length; i++) {
        var property = staticPropertyNames[i]
        clss[property]= staticProperties[property]
      }
    }
  }
  
  function createCallback(methodName) {
    if (typeof(this[methodName]) === "undefined") {
      MLAB.Core.throwException("Cannot create callback, because this method does not exist: " + methodName)
    }
    return this[methodName].bind(this)
  }
  
  function getClassName() { return this.__MLAB_CORE_internalClassName }
  
  function isInstance(clss) {
    return this.constructor == clss.prototype.constructor
  }
  
  var reservedClassMethods = [["callback", createCallback], 
                              ["getClassName", getClassName], 
                              ["isInstance", isInstance]]

  function addCommonClassMethods(namespace, clss, className) {
    for (var i=0; i<reservedClassMethods.length; i++) {
      var methodName = reservedClassMethods[i][0]
      var method = reservedClassMethods[i][1]
      if (methodName in clss.prototype && clss.prototype[methodName] !== method) {
        MLAB.Core.throwException("'" + methodName + "' is a reserved method name: " + className)
      }
    }
    clss.prototype.__MLAB_CORE_internalClassName = "MLAB." + namespace.getName() + "." + className
    clss.prototype.callback = createCallback
    clss.prototype.isInstance = isInstance
    clss.prototype.getClassName = getClassName
  }
  
  /**
   * 
   */
  function createClass(namespace, className, properties, staticProperties,  superClass) {
    if (className in namespace) {
      MLAB.Core.throwException("Another class with this name is already defined: " + className)
    }
    if (typeof(properties) !== "object") {
      MLAB.Core.throwException("Expected an object as properties, but got " + typeof(properties) + ". " +
                               "Use deriveClass() if you want to derive " + className + 
                               " from another class.")
    }
    if (typeof(superClass) !== "undefined" && typeof(superClass) !== "function") {
      MLAB.Core.throwException("Expected a constructor as super class, but got " + typeof(superClass) + 
                               ". Use defineClass() if you do not want to derive " + className + 
                               " from another class.")
    }
    if (!properties.hasOwnProperty(className)) {
      MLAB.Core.throwException("No constructor for this class defined: " + className)
    }
    var newClass = properties[className]
    // delete the constructor, so that is not copied by copyOwnProperties() below
    delete properties[className]
    var F = function() {}
    if (typeof(superClass) !== "undefined") {
      F.prototype = superClass.prototype
      newClass.super = superClass.prototype
      if (superClass.prototype.constructor === Object.prototype.constructor) {
        superClass.prototype.constructor = superClass
      }
    }
    newClass.prototype = new F()
    newClass.prototype.constructor = newClass   
    copyOwnProperties(newClass, properties, staticProperties)
    addCommonClassMethods(namespace, newClass, className)
    namespace[className] = newClass
  }
  
  Namespace = function(name) {
    var _name = name
    
    /**
     * 
     */
    this.getName = function() { return _name }
    
    this.defineClass = function(className, properties, staticProperties) {
      createClass(this, className, properties, staticProperties)
    }
    this.deriveClass = function(className, superClass, properties, staticProperties) {
      createClass(this, className, properties, staticProperties, superClass)
    }
  }
  
  this.createNamespace = function(name) {
    if (name in MLAB) {
      MLAB.Core.throwException("Another namespace with this name is already defined: " + name)
    }
    MLAB[name] = new Namespace(name)
  }
  
})()

MLAB.createNamespace("Core")

MLAB.Core.getStackTrace = function (depth) {
  var stackTrace = []
  try {
    throw ""
  } catch(e) {
    if (e.stack) {
      var lines = e.stack.split('\n')
      for (var i=0; i<lines.length; i++) {
        stackTrace.push(lines[i])
      }
      // remove this stack
      stackTrace.shift()
    }
  }
  if (stackTrace.length === 0) {
    var caller = arguments.callee.caller
    var count = 30;
    while (caller && count>0) {
      var callerString = caller.toString()
      var name = callerString.substring(callerString.indexOf("function") + 8, callerString.indexOf('')) || 'anonymous'
      stackTrace.push(name)
      caller = caller.caller
      count--;
    }
  }
  
  // remove the specified depth from the callstack
  for (var i=0; i<depth; i++) { stackTrace.shift() }
  return stackTrace.join("\n")
}

MLAB.Core.throwException = function(message) {
  var s = message + "\n" + MLAB.Core.getStackTrace(depth=2)
  throw new Error(s)
}

MLAB.Core.assert = function(expression, message) {
  if (!expression) {
    MLAB.Core.throwException("Assertion failed: " + message)
  }
}
