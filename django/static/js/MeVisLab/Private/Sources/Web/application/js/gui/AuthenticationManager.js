/** \class MLAB.Core.AuthenticationManager
 * 
 */
MLAB.GUI.deriveClass("AuthenticationManager", MLAB.Core.Object, {
  AuthenticationManager: function() {
    MLAB.GUI.AuthenticationManager.super.constructor.call(this)
    this.registerSignal("authenticateModuleContexts")
    this._authentication = ["",""]
    this._unauthenticatedModuleContexts = []
  },
  
  setLogger: function(logger) {
    this._logger = logger
  },
  
  /** \fn MLAB.Core.AuthenticationManager.getAuthentication
   * 
   * Returns the authentication data.
   * 
   * \return An array containing the username and password strings.
   */
  getAuthentication: function() { return this._authentication },
  
  /** \fn MLAB.Core.AuthenticationManager.setAuthentication
   * 
   * Sets the authentication data.
   * 
   * \param username A string.
   * \param password A base64 encoded string.
   */
  setAuthentication: function(username, password) { this._authentication = [username, password] },
  
  /** \fn MLAB.Core.AuthenticationManager.addUnauthenticatedModuleContext
   * 
   * \param moduleContext An MLAB.Core.ModuleContext instance.
   */
  addUnauthenticatedModuleContext: function(moduleContext) {
    this._unauthenticatedModuleContexts.push(moduleContext)
  },
  
  /** \fn MLAB.Core.AuthenticationManager.addUnauthenticatedModuleContext
   * 
   * Returns true if at least one unauthenticated module context exists.
   * 
   * \return Returns true or false.
   */
  hasAnyUnauthenticatedModuleContext: function() { return this._unauthenticatedModuleContexts.length > 0 },
  
  /** \fn MLAB.Core.AuthenticationManager.getUnauthenticatedModuleContexts
   * 
   * Returns all unauthenticated module context.
   * 
   * \return Returns an array of MLAB.Core.ModuleContext instances.
   */
  getUnauthenticatedModuleContexts: function() { return this._unauthenticatedModuleContexts },
  
  /** \fn MLAB.Core.AuthenticationManager.authenticateModuleContexts
   * 
   */
  authenticateModuleContexts: function() {
    try {
      this.emit("authenticateModuleContexts")
      // try to connect again
      for (var i=0; i<this._unauthenticatedModuleContexts.length; i++) {
        this._unauthenticatedModuleContexts[i].authenticate(this._authentication[0], this._authentication[1])
      }
      this._unauthenticatedModuleContexts = []
    } catch(e) {
      this._logger.logException(e)
    }
  },
  
  /** \fn MLAB.Core.AuthenticationManager.requestAuthentication
   * 
   * Asks the user for a username and passwort to be passed as authentication to
   * the modules. Needs to be implemented in a framework. This method must
   * then call authenticateModuleContexts()
   */
  requestAuthentication: function() {
    MLAB.Core.throwException("requestAuthentication() is not implemented")
  },
})
