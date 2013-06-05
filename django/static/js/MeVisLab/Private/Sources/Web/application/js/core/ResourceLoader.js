/** \class MLAB.Core.Resource
 * 
 * The url to the resource may be relative to the given resources url.
 * A DOM node with the given type and attributes will finally be created from this resource.
 * 
 * \param type The DOM node type, either "script" or "link".
 * \param url An absolute or relative or to the resource.
 * \param attributes The attributes for the DOM node.
 * \param resourcesUrl An optional parameter for resolving relative urls.
 */
MLAB.Core.defineClass("Resource", {
  Resource: function (url, resourcesUrl) {
    this._url = url
    if ((url[0] !== "/") && !url.match(/(^[a-zA-Z]+:.*)/i)) {
      // a relative url has been given, prepend the root directory
      this._url = resourcesUrl + url
    }
    this._loadingFinishedCallback = null
  },
  
  url: function() { return this._url },
    
  setLoadingFinishedCallback: function(loadingFinishedCallback) {
    this._loadingFinishedCallback = loadingFinishedCallback
  },
  
  _onLoad: function() {
    this._loadingFinishedCallback(this)
  },
  
  _onError: function() {
    // additionally we could do some error handling here
    this._onLoad()
  }
})


/** \class MLAB.Core.ScriptResource(MLAB.Core.Resource)
 * 
 * Resource class for scripts.
 * 
 * \param url An absolute or relative or to the resource.
 * \param resourcesUrl An optional parameter for resolving relative urls.
 */
MLAB.Core.deriveClass("ScriptResource", MLAB.Core.Resource, {
  ScriptResource: function(url, resourcesUrl) {
    MLAB.Core.ScriptResource.super.constructor.call(this, url, resourcesUrl)
  },
  
  load: function() {
    var element = document.createElement("script")
    element.setAttribute("type", "text/javascript")
    element.src = this._url
    element.onload = this.callback("_onLoad")
    element.onerror = this.callback("_onError")
    document.getElementsByTagName("head")[0].appendChild(element)
  },
})


/** \class MLAB.Core.StyleResource(MLAB.Core.Resource)
 * 
 * Resource class for css files.
 * 
 * \param url An absolute or relative or to the resource.
 * \param resourcesUrl An optional parameter for resolving relative urls.
 */
MLAB.Core.deriveClass("StyleResource", MLAB.Core.Resource, {
  StyleResource: function(url, resourcesUrl) {
    MLAB.Core.StyleResource.super.constructor.call(this, url, resourcesUrl)
    this._pollTimer = new MLAB.Core.Timer()
    this._pollTimer.setInterval(10)
    this._styleNode = null
  },
  
  load: function() {
    if (MLAB.Core.SystemInfo.isIE()) {
      // TODO: this code is not tested
      this._styleNode = document.createElement("link")
      this._styleNode.rel = "stylesheet"
      this._styleNode.type = "text/css"
      this._styleNode.href = this._url
      this._styleNode.onload = this.callback("_onLoad")
      this._styleNode.onerror = this.callback("_onError")
      
    } else if (MLAB.Core.SystemInfo.isWebKit()) {
      this._styleNode = document.createElement("link")
      this._styleNode.rel = "stylesheet"
      this._styleNode.type = "text/css"
      this._styleNode.href = this._url
      this._pollTimer.setCallback(this.callback("_pollWebKit"))
      this._pollTimer.start()
      
    } else if (MLAB.Core.SystemInfo.isGecko()) {
      this._styleNode = document.createElement("style")
      this._styleNode.type = "text/css"
      this._styleNode.innerHTML = "@import url(" + this._url + ")"
      this._pollTimer.setCallback(this.callback("_pollGecko"))
      this._pollTimer.start()
      
    } else {
      // not sure what we can do, just add the style and call _onLoad()
      // after a short timeout
      this._styleNode = document.createElement("link")
      this._styleNode.rel = "stylesheet"
      this._styleNode.type = "text/css"
      this._styleNode.href = this._url
      this._pollTimer.setSingleShot(true)
      this._pollTimer.setCallback(this.callback("_onLoad"))
      this._pollTimer.start()
    }
    
    document.getElementsByTagName("head")[0].appendChild(this._styleNode)
  },
  
  _pollGecko: function() {
    try {
      hasRules = !!this._styleNode.sheet.cssRules
      this._pollTimer.stop()
      this._onLoad()
    } catch (e) {
      // still not loaded
      if (this._pollTimer.getIntervalCount() > 1000) {
        this._pollTimer.stop()
        // the style sheet could not be loaded by now, so issue an error
        this._onError()
      }
    }
  },
  
  _pollWebKit: function() {
    var styleSheets = document.styleSheets

    for (var i=0; i<styleSheets.length; i++) {
      if (styleSheets[i].href === this._styleNode.href) {
        this._pollTimer.stop()
        this._onLoad()
        break
      }
    }
    
    if (this._pollTimer.getIntervalCount() > 1000) {
      this._pollTimer.stop()
      // the style sheet could not be loaded by now, so issue an error
      this._onError()
    }
  },
  
}, {
  // static members
  _cssId: 0,
  
  getNextCSSId: function() {
    return MLAB.Core.StyleResource._cssId++
  },
})


/** \class MLAB.Core.ResourceLoader
 * 
 * This class loads resources by creating and appending DOM nodes to the HTML header.
 * If all resources finished loading, then the callback is called. The resources are
 * loaded sequentially, because the contain objects that depend on each other.
 * 
 * \param resourceList An array containing MLAB.Core.Resource instances.
 * \param loadingFinishedCallback A callback that is called when all resources have finished loading.
 */
MLAB.Core.defineClass("ResourceLoader", { 
  ResourceLoader: function(resourceList, loadingFinishedCallback) {
    this._pendingResources = resourceList
    this._loadingFinishedCallback = loadingFinishedCallback
  },
  
  /** \fn MLAB.Core.ResourceLoader.loadResources
   * 
   * Loads all resources. Because the loading is asynchronous the resources are not
   * necessarily loaded when this method is finished. Use the loading finished callback
   * to get informed when all resources have finished loading.
   */
  loadResources: function() {
    MLAB.Core.throwException("Not implemented")
  },
})

/** \class MLAB.Core.SequentialResourceLoader(MLAB.Core.ResourceLoader)
 * 
 */
MLAB.Core.deriveClass("SequentialResourceLoader", MLAB.Core.ResourceLoader, { 
  SequentialResourceLoader: function(resourceList, loadingFinishedCallback) {
    MLAB.Core.SequentialResourceLoader.super.constructor.call(this, resourceList, loadingFinishedCallback)
  },
  
  /** \fn MLAB.Core.ResourceLoader._resourceLoaded
   * 
   * Remote the given resource from the list of pending resources and calls
   * the loading finished callback if the list is cleared.
   * 
   * \param resource An MLAB.Core.Resource instance.
   */
  _resourceLoaded: function(resource) {
    this._pendingResources.remove(resource)
    if (this._pendingResources.length === 0) {
      this._loadingFinishedCallback()
    } else {
      this._loadNextResource()
    }
  },

  loadResources: function() {
    if (this._pendingResources.length > 0) {
      this._loadNextResource()
    } else {
      this._loadingFinishedCallback()
    }
  },
  
  _loadNextResource: function() {
    var resource = this._pendingResources[0]
    resource.setLoadingFinishedCallback(this.callback("_resourceLoaded"))
    resource.load()
  },
})

/** \class MLAB.Core.ParallelResourceLoader(MLAB.Core.ResourceLoader)
 * 
 */
MLAB.Core.deriveClass("ParallelResourceLoader", MLAB.Core.ResourceLoader, { 
  ParallelResourceLoader: function(resourceList, loadingFinishedCallback) {
    MLAB.Core.ParallelResourceLoader.super.constructor.call(this, resourceList, loadingFinishedCallback)
  },
  
  /** \fn MLAB.Core.ResourceLoader._resourceLoaded
   * 
   * Remote the given resource from the list of pending resources and calls
   * the loading finished callback if the list is cleared.
   * 
   * \param resource An MLAB.Core.Resource instance.
   */
  _resourceLoaded: function(resource) {
    this._pendingResources.remove(resource)
    if (this._pendingResources.length === 0) {
      this._loadingFinishedCallback()
    }
  },
  
  /** \fn MLAB.Core.ResourceLoader.loadResources
   * 
   * Loads all resources. Because the loading is asynchronous the resources are not
   * necessarily loaded when this method is finished. Use the loading finished callback
   * to get informed when all resources have finished loading.
   */
  loadResources: function() {
    if (this._pendingResources.length > 0) {
      for (var i=0; i<this._pendingResources.length; i++) {
        var resource = this._pendingResources[i]
        resource.setLoadingFinishedCallback(this.callback("_resourceLoaded"))
        resource.load()
      }
    } else {
      this._loadingFinishedCallback()
    }
  },
})

/** \class MLAB.Core.ResourceManager
 * 
 * Manages loading of script and css resources.
 * 
 * \param resourcesBaseUrl The root directory to resolve relative resource urls.
 */
MLAB.Core.defineClass("ResourceManager", { 
  ResourceManager: function(resourcesBaseUrl) {
    this._loadedScriptUrls = new Array()
    this._loadedCSSUrls = new Array()
    this._jsLoader = null
    this._cssLoader = null
    this._resourcesBaseUrl = resourcesBaseUrl
    if (resourcesBaseUrl[resourcesBaseUrl.length-1] !== '/') {
      this._resourcesBaseUrl = resourcesBaseUrl + '/'
    }
  },
  
  getResourcesBaseUrl: function() {
    return this._resourcesBaseUrl
  },
  
  /** \fn MLAB.Core.ResourceManager.loadResources
   * 
   * Loads the given scripts and css files. Finally it calls the loading finished callback
   * when all resources have finished loading. 
   * 
   * \param scriptModules An array of absolute or relative script urls.
   * \param cssModules An array of absolute or relative css urls.
   * \param loadingFinishedCallback The callback function when loading of the resources is finished.
   * \param jsLoader An optional loader. By default MLAB.Core.SequentialResourceLoader is used.
   * \param cssLoader An optional loader. By default MLAB.Core.ParallelResourceLoader is used.
   */
  loadResources: function(scriptUrls, cssUrls, loadingFinishedCallback, jsLoader, cssLoader) {
    if (this._cssLoader !== null) {
      MLAB.Core.throwException("The css loader is still active")
    }
    if (this._jsLoader !== null) {
      MLAB.Core.throwException("The js loader is still active")
    }
    this._loadingFinishedCallback = loadingFinishedCallback

    var jsResourceList = []
    var cssResourceList = []
    
    for (var i=0; i<scriptUrls.length; i++) {
      if (this._loadedScriptUrls.indexOf(scriptUrls[i]) === -1) {
        this._loadedScriptUrls.push(scriptUrls[i])
        jsResourceList.push(new MLAB.Core.ScriptResource(scriptUrls[i], this._resourcesBaseUrl))
      }
    }
    
    for (var i=0; i<cssUrls.length; i++) {
      if (this._loadedCSSUrls.indexOf(cssUrls[i]) === -1) {
        this._loadedCSSUrls.push(cssUrls[i])
        cssResourceList.push(new MLAB.Core.StyleResource(cssUrls[i], this._resourcesBaseUrl))
      }
    }

    if (this._jsLoader !== null) {
      MLAB.Core.throwException("Resource loader is already active")
    }
    
    if (!jsLoader) {
      jsLoader = MLAB.Core.SequentialResourceLoader
    }
    if (!cssLoader) {
      cssLoader = MLAB.Core.ParallelResourceLoader
    }
    this._jsLoader = new jsLoader(jsResourceList, this.callback("_jsResourcesLoaded"))
    this._cssLoader = new cssLoader(cssResourceList, this.callback("_cssResourcesLoaded"))
    this._jsLoader.loadResources()
    this._cssLoader.loadResources()
  },
  
  _jsResourcesLoaded: function() {
    this._jsLoader = null
    this._loaderFinished()
  },
  
  _cssResourcesLoaded: function() {
    this._cssLoader = null
    this._loaderFinished()
  },
  
  _loaderFinished: function() {
    if (this._jsLoader === null && this._cssLoader === null) {
      // set this._loadingFinishedCallback to null before the callback is called,
      // because the callback might load resources again, and we would overwrite another
      // new callback with
      var callback = this._loadingFinishedCallback
      this._loadingFinishedCallback = null
      callback()
    }
  },
})
