MLAB.Core.convertMDLValueToBool = function(stringValue) {
  return ["true", "yes", "1", "on"].indexOf(stringValue.toLowerCase()) >= 0
}

MLAB.Core.defineClass("Tree", {
  Tree: function(json) {
    this.json = json
    this.json.tree = this
    this._setup()
  },
  
  _setup: function() {
    if (this.json.children) {
      for (var i=0; i<this.json.children.length; i++) {
        var child = this.json.children[i]
        child.tree = new MLAB.Core.Tree(child)
      }
    }
  },
  
  append: function(child) {
    if (typeof(this.json.children) === "undefined") {
      this.json.children = []
    }
    this.json.children.push(child.json)
  },
  
  getName: function() { return this.json.name },
  getValue: function() { return this.json.value },
  count: function() { return this.json.children ? this.json.children.length : 0},
  child: function(index) { return this.json.children[index].tree },
  childValue: function(name, defaultValue) {
    var c = this.get(name)
    if (c) {
      return c.json.value
    }
    return (typeof(defaultValue) === "undefined") ? "" : defaultValue
  },
  get: function(name) {
    if (this.json.children) {
      for (var i=0; i<this.json.children.length; i++) {
        if (this.json.children[i].name === name) {
          return this.json.children[i].tree
        }
      }
    }
    return null
  },
  getAll: function(name) {
    var result = []
    if (this.json.children) {
      for (var i=0; i<this.json.children.length; i++) {
        if (this.json.children[i].name === name) {
          result.push(this.json.children[i].tree)
        }
      }
    }
    return result
  },
})

MLAB.Core.encodeBase64 = function(s) {
  var abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  var r = ''
  var length = s.length/3
  if (s.length > length*3) { length += 1 }  
  for (var i=0; i<length; i++) {
    var idx = i*3
    var c0 = s.charCodeAt(idx++)
    if (idx < s.length) {
      var c1 = s.charCodeAt(idx++)
      if (idx < s.length) {
        var c2 = s.charCodeAt(idx)
        var b = (c0<<16) | (c1<<8) | c2
        r += abc.charAt((b>>18) & 63) + abc.charAt((b>>12) & 63) + abc.charAt((b>>6) & 63) + abc.charAt(b & 63)
      } else {
        var b = (c0<<16) | (c1<<8)
        r += abc.charAt((b>>18) & 63) + abc.charAt((b>>12) & 63) + abc.charAt((b>>6) & 63) + '='
      }
    } else {
      var b = (c0<<16)
      r += abc.charAt((b>>18) & 63) + abc.charAt((b>>12) & 63) + '=='
    }
  }
  return r
}


MLAB.Core.decodeBase64 = function(s) {
  var abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  var r = ''
  var length = s.length/4
  for (var i=0; i<length; i++) {
    var idx = i*4
    var c0 = s.charAt(idx++)
    var c1 = s.charAt(idx++)
    var c2 = s.charAt(idx++)
    var c3 = s.charAt(idx)
    
    if (c2 === "=") {
      var b = (abc.indexOf(c0)<<18) | (abc.indexOf(c1)<<12)
      r += String.fromCharCode((b>>16) & 255)
    } else if (c3 === "=") {
      var b = (abc.indexOf(c0)<<18) | (abc.indexOf(c1)<<12) | (abc.indexOf(c2)<<6)
      r += String.fromCharCode((b>>16) & 255, (b>>8) & 255)
    } else {
      var b = (abc.indexOf(c0)<<18) | (abc.indexOf(c1)<<12) | (abc.indexOf(c2)<<6) | abc.indexOf(c3)
      r += String.fromCharCode((b>>16) & 255, (b>>8) & 255, b & 255)
    }
  }
  return r
}

;(function() {
  
  this.getTextContent = function(htmlString) {
    var d = document.createElement("div")
    d.innerHTML = htmlString.replace(/<br>/g,"\n")
    return d.textContent
  }
  
  /** \fn MLAB.Core.translatePath
   * 
   * Translates a path beginning with a package variable \$(MLAB_Xxxx_Yyyy) to an url
   * beginning with MLAB_ROOT. Returns null if the given path is null.
   * 
   * For example, $(MLAB_MeVisLab_Standard)/Modules/Macros is translated into 
   * http://www.myserver.de/Packages/MeVisLab/Standard/Modules/Macros, where the url to MLAB_ROOT
   * is http://www.myserver.de/Packages.
   * 
   * \see MLAB.GUI.ApplicationSettings.getURLToMLABRoot()
   * 
   * \param path A path that begins with a package variable, e.g.: \$(MLAB_Xxxx_Yyyy)/Modules/Macros, or null.
   * \returns Returns the absolute url containing the url to MLAB_ROOT 
   */
  this.translatePath = function(path) {
    if (path === null) {
      return null
    }
    // returns a list of matches:
    var matches = /^\$\(MLAB_\w+_\w+\)/i.exec(path)
    if (matches) {
      var match = matches[0]
      path = path.substring(match.length)
      match = match.substring(7, match.length-1).replace("_", "/")
      path = MLAB.GUI.Application.getSettings().getURLToMLABRoot() + match + path
    }
    return path
  }
  
  var charCode0 = "0".charCodeAt(0)
  var charCode9 = "9".charCodeAt(0)
  var charCodea = "a".charCodeAt(0)
  var charCodez = "z".charCodeAt(0)
  var charCodeA = "A".charCodeAt(0)
  var charCodeZ = "Z".charCodeAt(0)

  /** \fn MLAB.Core.isLetterOrNumber
   * 
   * TODO: This function handles only ASCII!
   * 
   * @param charCode
   */
  this.isLetterOrNumber = function(charCode) {
    return ((charCode >= charCode0) && (charCode <= charCode9)) ||
            ((charCode >= charCodea) && (charCode <= charCodez)) ||
            ((charCode >= charCodeA) && (charCode <= charCodeZ))
  }
  
  this.roundDoubleToFloat = function(value) {
    return parseFloat(value.toFixed(6))
  }
  
}).apply(MLAB.Core)
