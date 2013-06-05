/** \class MLAB.Core.BaseFieldHandlerBase
 * Base class for base field handlers.
 * 
 */
MLAB.Core.defineClass("BaseFieldHandlerBase", {
  BaseFieldHandlerBase: function(baseField) {
    this._baseField = baseField
  },
  
  /** \fn MLAB.Core.BaseFieldHandlerBase.sendBaseFieldMessage
   * 
   * Passes the handled field, the message class, and the data to
   * MLAB.Core.Module.sendBaseFieldMessage(). 
   * 
   * \param messageClass A subclass of MLAB.Core.RemoteMessage
   * \param data The message data.
   */
  sendBaseFieldMessage: function(messageClass, data) {
    this._baseField.getFieldOwner().sendBaseFieldMessage(this._baseField, messageClass, data)
  }
})

/** \class MLAB.Core.BaseFieldHandlerFactory
 * 
 * This factory class creates handlers for base fields. See also MLAB.Core.BaseField.handleMessage(). 
 */
MLAB.Core.defineClass("BaseFieldHandlerFactorySingleton", {
  BaseFieldHandlerFactorySingleton: function() {
    this._handlerClasses = new Object()
  },
  
  /** \fn MLAB.Core.BaseFieldHandlerFactory.registerHandler
   * 
   * Registers the class of a base field handler for the given base field type. Only
   * one handler may be registered for one base field type.
   * 
   * \param baseFieldType The base field type.
   * \param handlerClass The base field handler class.
   */
  registerHandler: function(baseFieldType, handlerClass) {
    if (name in this._handlerClasses) {
      MLAB.Core.throwException("Base handler already registered: " + baseFieldType)
    }
    this._handlerClasses[baseFieldType] = handlerClass
  },
  
  /** \fn MLAB.Core.BaseFieldHandlerFactory.createHandler
   * 
   * Creates a base field handler for the type of the given base field and returns it.
   * Throws an exception if there is no handler registered for the base type.
   * 
   * \param baseField An MLAB.Core.BaseField.
   * \return The base field handler.
   */
  createHandler: function(baseField) {
    if (!(baseField.getBaseType() in this._handlerClasses)) {
      MLAB.Core.throwException("No base handler registered for this base type: " + baseField.getBaseType())
    }
    var handler = this._handlerClasses[baseField.getBaseType()]
    return new handler(baseField)
  },
})

MLAB.Core.BaseFieldHandlerFactory = new MLAB.Core.BaseFieldHandlerFactorySingleton()
