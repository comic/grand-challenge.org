/** \defgroup Fields Fields
 * 
 * These are the fields.
 */

/** \class MLAB.Core.Field
 * 
 * This class is based on the MeVisLab class ::MLAB.Core.Field. The JavaScript fields are synchronized 
 * with the fields in MeVisLab through web socket messages. If the field value is changed
 * in JavaScript it is updated in the MeVisLab process and vice versa.
 * 
 * The signal "fieldChanged(field)" is emitted whenever the field's value changes. 
 *
 * \ingroup Fields
 */
MLAB.Core.deriveClass("Field", MLAB.Core.Object, {
  Field: function() {
    MLAB.Core.Field.super.constructor.call(this)

    this.registerSignal("fieldChanged")

    this._fieldOwner = null
    this._name = null
    this._type = null
    this._flags = null
    this._value = ''
    this._listeners = []
    this._lastChangeSerialID = -1
  },
  
  /** \fn MLAB.Core.Field.setup
   *
   * Sets the field up. This method should only be called by MLABModule to initialize the field.
   * Each field has an owner, which needs to provide logging and message handling methods.
   * 
   * \param name The field name string.
   * \param type The field type string.
   * \param flags The field flags, which can include MLAB.Core.Field.INPUT_FIELD, MLAB.Core.Field.OUTPUT_FIELD, MLAB.Core.Field.INOUT_FIELD and MLAB.Core.Field.NON_PERSISTENT_FIELD.
   * \param fieldOwner The field owner (which is usually an MLABModule). 
   */
  setup: function(name, type, flags, fieldOwner) {
    this._fieldOwner = fieldOwner
    this._name = name
    this._type = type
    this._flags = flags
  },
  
  /** \fn MLAB.Core.Field.getFlags
   * 
   * Returns the flags.
   * 
   * \return Returns the flags.
   */
  getFlags: function() { return this._flags },

  /** \fn MLAB.Core.Field.isInput
   * 
   * Returns true if this field is an input field.
   * 
   * \return Returns true if MLAB.Core.Field.INPUT_FIELD is included in the flags, false otherwise.
   */
  isInput: function() { return (this._flags & MLAB.Core.Field.INPUT_FIELD) !== 0 },
  
  /** \fn MLAB.Core.Field.isOutput
   * 
   * Returns true if this field is an output field.
   * 
   * \return Returns true if MLAB.Core.Field.OUTPUT_FIELD is included in the flags, false otherwise.
   */
  isOutput: function() { return (this._flags & MLAB.Core.Field.OUTPUT_FIELD) !== 0 },
  
  /** \fn MLAB.Core.Field.isInOut
   * 
   * Returns true if this field is an input and output field.
   * 
   * \return Returns true if MLAB.Core.Field.INOUT_FIELD is included in the flags, false otherwise.
   */
  isInOut: function() { return (this._flags & MLAB.Core.Field.INOUT_FIELD) !== 0 },
  
  /** \fn MLAB.Core.Field.isParameterField
   * 
   * Returns true if this field is a parameter field.
   * 
   * \return Returns true if this field is neither an input field, nor an output field.
   */
  isParameterField: function() { return !this.isInput() && !this.isOutput() },
  
  /** \fn MLAB.Core.Field.isPersistent
   * 
   * Returns true if this field is persistent.
   * 
   * \return Returns false if MLAB_NON_PERSISTENT_FIELD is included in the flags, true otherwise.
   */
  isPersistent: function() { return (this._flags & MLAB_NON_PERSISTENT_FIELD) === 0 },
  
  /** \fn MLAB.Core.Field.getType
   * 
   * Returns the field type.
   * 
   * \return The field type string.
   */
  getType: function() { return this._type },
  
  /** \fn MLAB.Core.Field.getValue
   * 
   * Returns the field value.
   * 
   * \return The field value. The type of the value depends on the field type.
   */
  getValue: function() { return this._value },
  
  /** \fn MLAB.Core.Field.getName
   * 
   * Returns the field name.
   * 
   * \return The field name string.
   */
  getName: function() { return this._name },
  
  /** \fn MLAB.Core.Field.getFieldOwner
   * 
   * Returns the field owner.
   * 
   * \return The field owner (usually an MLABModule).
   */
  getFieldOwner: function() { return this._fieldOwner },
  
  /** \fn MLAB.Core.Field.isBaseField
   * 
   * Returns true if this is an MLAB.Core.BaseField.
   */
  isBaseField: function() { return false },
  
  /** \fn MLAB.Core.Field.isBoolField
   * 
   * Returns true if this is an MLAB.Core.BoolField.
   */
  isBoolField: function() { return false },
  
  /** \fn MLAB.Core.Field.isColorField
   * 
   * Returns true if this is an MLAB.Core.ColorField.
   */
  isColorField: function() { return false },
  
  /** \fn MLAB.Core.Field.isDoubleField
   * 
   * Returns true if this is an MLAB.Core.DoubleField.
   */
  isDoubleField: function() { return false },
  
  /** \fn MLAB.Core.Field.isEnumField
   * 
   * Returns true if this is an MLAB.Core.EnumField.
   */
  isEnumField: function() { return false },
  
  /** \fn MLAB.Core.Field.isFloatField
   * 
   * Returns true if this is an MLAB.Core.FloatField.
   */
  isFloatField: function() { return false },
  
  /** \fn MLAB.Core.Field.isIntegerField
   * 
   * Returns true if this is an MLAB.Core.IntegerField.
   */
  isIntegerField: function() { return false },
  
  /** \fn MLAB.Core.Field.isMatrixField
   * 
   * Returns true if this is an MLAB.Core.MatrixField.
   */
  isMatrixField: function() { return false },
  
  /** \fn MLAB.Core.Field.isNumberField
   * 
   * Returns true if this is an MLAB.Core.NumberField derived class.
   */
  isNumberField: function() { return false },
  
  /** \fn MLAB.Core.Field.isStringField
   * 
   * Returns true if this is an MLAB.Core.StringField.
   */
  isStringField: function() { return false },
  
  /** \fn MLAB.Core.Field.isTriggerField
   * 
   * Returns true if this is an MLAB.Core.TriggerField.
   */
  isTriggerField: function() { return false },
  
  /** \fn MLAB.Core.Field.isVectorField
   * 
   * Returns true if this is an MLAB.Core.VectorField.
   */
  isVectorField: function() { return false },
  
  /** \fn MLAB.Core.Field.addListener
   * 
   * Adds a listener to this field. The listener must implement a fieldChanged() method,
   * which is called whenever the field changes.
   *
   * Consider using the "fieldChanged" signal instead of adding a listener.
   * 
   * \param listener An object with a fieldChanged() method. This field is the only argument that is passed to the method.
   */
  addListener: function(listener) {
    if (listener) {
      this._listeners.push(listener)
    } else {
      MLAB.Core.throwException("MLAB.Core.Field.addListener: invalid field listener given: " + listener)
    }
  },
  
  /** \fn MLAB.Core.Field.touch
   * 
   * Triggers a notification of all field listeners in JavaScript and in the MeVisLab process
   * on the server. The field value is not changed.
   */
  touch: function() {
    this.setValue(this._value)
  },
  
  /** \fn MLAB.Core.Field.setValue
   * 
   * Sets the value. All field listeners in JavaScript and in the MeVisLab process on the server
   * get notified.
   * 
   * \param value The new field value which must be of the expected type.
   */
  setValue: function(value) {
    // update the value and notify all client side field listeners,
    // because the server does not send another MLAB.Core.ModuleSetFieldValuesMessage.
    this.updateValue(value)
    this._fieldOwner.fieldValueChanged(this)
  },

  /** \fn MLAB.Core.Field.updateValue
   * 
   * Sets the field value an notifies all JavaScript field listeners. The field value is not
   * update in the MeVisLab process and no server side listener will get notified.
   * 
   * \param value The new value.
   */
  updateValue: function(value) {
    this._value = value
    this.notifyListeners()
  },
  
  /** \fn MLAB.Core.Field.notifyListeners
   * 
   * Notifies all JavaScript field listeners, but not the field listeners in the MeVisLab process
   * on the server.
   */
  notifyListeners: function() {
    for (var i=0; i<this._listeners.length; i++) {
      try {
        this._listeners[i].fieldChanged(this)
      } catch (e) {
        this._fieldOwner.logException(e)
      }
    }
    this.emit("fieldChanged", this)
  },
  
  /** \fn MLAB.Core.Field._valueToString 
   * 
   * Converts the given value to string.
   * 
   * \returns The value as string.
   */
  _valueToString: function(value) {
    MLAB.Core.throwException("_valueToString() is not implemented " + this)
  },
  
  /** \fn MLAB.Core.Field._valueFromString
   * 
   * Converts the given string to the value type.
   * 
   * \returns The value corresponding to the field type.
   */
  _valueFromString: function(value) {
    MLAB.Core.throwException("_valueFromString() is not implemented " + this)
  },
  
  /** \fn MLAB.Core.Field.stringValue
   * 
   * Returns the value as string.
   * 
   * \returns The value as string.
   */
  stringValue: function() {
    return this._valueToString(this._value)
  },
  
  /** \fn MLAB.Core.Field.setStringValue
   * 
   * Sets the value as string.
   * 
   * \param value The value as string.
   */
  setStringValue: function(value) {
    this.setValue(this._valueFromString(value))
  },
  
  /** \fn MLAB.Core.Field.updateStringValue
   * 
   * Does the same as updateValue() except that the value is a string.
   * 
   * \param value A string value.
   */
  updateStringValue: function(value) {
    this.updateValue(this._valueFromString(value))
  },
  
  /** \fn MLAB.Core.Field.lastChangeSerialID
   * 
   * Get a virtual time stamp when the value was last changed from the client.
   */
  lastChangeSerialID: function() {
    return this._lastChangeSerialID
  },

  /** \fn MLAB.Core.Field.setLastChangeSerialID
   * 
   * Set the virtual time stamp when the value is changed from the client.
   */
  setLastChangeSerialID: function(timestamp) {
    this._lastChangeSerialID = timestamp
  }
}, {
  /** Flag for MLAB.Core.Field which indicates that it is an input field. */ 
  INPUT_FIELD: 1,
  /** Flag for MLAB.Core.Field which indicates that it is an output field. */
  OUTPUT_FIELD: 2,
  /** Flag for MLAB.Core.Field which indicates that it is an input and output field. */
  INOUT_FIELD: 3,
  /** Flag for MLAB.Core.Field which indicates that it is a non-persistent field. */
  NON_PERSISTENT_FIELD: 4

})


/** \class MLAB.Core.BaseField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("BaseField", MLAB.Core.Field, {
  BaseField: function() {
    MLAB.Core.BaseField.super.constructor.call(this)
    this._value = null
    this._generationId = -1
    this._handler = null
    this._baseType = null
  },
  
  isBaseField: function() { return true },

  /** \fn MLAB.Core.BaseField.getGenerationId
   * 
   * Returns the generation id of this base field. The generation ID is incremented each
   * time the base object of the field changes.
   * 
   * \return Returns an integer, which may be -1 if the base field is uninitialized.
   */
  getGenerationId: function() { return this._generationId },
  
  /** \fn MLAB.Core.BaseField.getBaseType
   * 
   * Returns the type of the current base object. For example, it may be "RemoteRendering"
   * or "AbstractItemModel".
   * 
   * \return Returns the base type string.
   */
  getBaseType: function() { return this._baseType },
  
  /** \fn MLAB.Core.BaseField.getHandler
   * 
   * Returns the handler that handles the messages for this field.
   * 
   * \return An object that handles the base field messages for this field. It implements a handleMessage() method.
   */
  getHandler: function() { return this._handler },
  
  /** \fn MLAB.Core.BaseField.handleMessage
   * 
   * Handles base field messages by passing it to the handler. If the message is a MLAB.Core.ModuleBaseFieldTypeMessage, then 
   * MLAB.Core.BaseFieldHandlerFactory.createHandler() is called to create a new handler and all 
   * JavaScript field listeners are notified. 
   * 
   * \param message A message that is derived from MLAB.Core.BaseFieldMessage.
   */
  handleMessage: function(message) {
    if (typeof(message.baseGeneration) !== "number") {
      MLAB.Core.throwException("Message baseGeneration is not a number")
    }
    if (message.type === MLAB.Core.MSG_MODULE_BASE_FIELD_TYPE) {
      this._baseType = message.baseType
      this._generationId = message.baseGeneration
      this._handler = this._fieldOwner.createBaseFieldHandler(this)
      this.notifyListeners()
    }
    if (this._handler) {
      this._handler.handleMessage(message)
    }
  },

  // base fields have no real value in JavaScript
  _valueToString: function(value) { return value },
  _valueFromString: function(value) { return value },
})


/** \class MLAB.Core.BoolField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("BoolField", MLAB.Core.Field, {
  BoolField: function() {
    MLAB.Core.BoolField.super.constructor.call(this)
  },

  isBoolField: function() { return true },
  
  _valueFromString: function(value) {
    return MLAB.Core.convertMDLValueToBool(value.toLowerCase())
  },
  
  _valueToString: function(value) {
    return (value ? "TRUE" : "FALSE")
  },
})


/** \class MLAB.Core.ColorField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("ColorField", MLAB.Core.Field, {
  ColorField: function() {
    MLAB.Core.ColorField.super.constructor.call(this)
  },
  
  isColorField: function() { return true },
  
  _valueToString: function(value) {
    // TODO: this needs to be correctly implemented
    return value 
  },
  
  _valueFromString: function(value) {
    // TODO: this needs to be correctly implemented
    return value 
  },
})


/** \class MLAB.Core.NumberField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("NumberField", MLAB.Core.Field, {
  NumberField: function() {
    MLAB.Core.NumberField.super.constructor.call(this)
  
    // note that Number.MIN_VALUE is the smallest positive number closest to 0
    this._minValue = -Number.MAX_VALUE
    this._maxValue = Number.MAX_VALUE
  },
  
  /** \fn MLAB.Core.NumberField.getMaxValue
   * 
   * Returns the maximum value of this number field.
   * 
   * \return The maximum value. The type depends on the field type.
   */
  getMaxValue: function() { return this._maxValue },
  
  /** \fn MLAB.Core.NumberField.getMinValue
   * 
   * Returns the minimum value of this number field.
   * 
   * \return The minimum value. The type depends on the field type.
   */
  getMinValue: function() { return this._minValue },
  
  /** \fn MLAB.Core.NumberField.setMaxValue
   * 
   * Sets the maximum value of this number field.
   * 
   * \param value The maximum value.
   */
  setMaxValue: function(value) { this._maxValue = value },
  
  setMaxValueAsString: function(value) { this.setMaxValue(this._valueFromString(value)) },
  
  /** \fn MLAB.Core.NumberField.setMinValue
   * 
   * Sets the minimum value of this number field.
   * 
   * \param value The minimum value.
   */
  setMinValue: function(value) { this._minValue = value },
  
  setMinValueAsString: function(value) { this.setMinValue(this._valueFromString(value)) },
  
  isNumberField: function() { return true },
  
  _valueToString: function(value) { return value.toString() },

  updateValue: function(value) {
    if (isNaN(value)) {
      MLAB.Core.throwException("Attempt to set the value to NaN.")
    }
    MLAB.Core.NumberField.super.updateValue.call(this, value)
  },
})


/** \class MLAB.Core.DoubleField(MLAB.Core.NumberField)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("DoubleField", MLAB.Core.NumberField, {
  DoubleField: function() {
    MLAB.Core.DoubleField.super.constructor.call(this)
  },

  isDoubleField: function() { return true },
  
  _valueFromString: function(value) { 
    return parseFloat(value)
  },
})

/** \class MLAB.Core.EnumItem
 * \ingroup Fields
 */
MLAB.Core.defineClass("EnumItem", {
  EnumItem: function(value) {
    this._value = value
    this._title = ''
    this._createAutoTitle()
  },
  
  value: function() {
    return this._value
  },
  
  setTitle: function(title) {
    this._title = title
    if (!this._title) {
      this._title = this._createAutoTitle()
    } else {
      this._hasAutoTitle = false
    }
  },
  
  title: function() {
    return this._title
  },
  
  hasAutoTitle: function() {
    return this._hasAutoTitle
  },
  
  // TODO: MLABEnumField in MeVisLab creates automatic titles already. It should be send by a message
  // instead of implementing the automatic title creation here.
  //@{
  _createAutoTitle: function() {
    if (this._title.length > 0) {
      return
    } else {
      this._hasAutoTitle = true
    }
    
    if (this._value.length === 0) { return }
    
    var code_a = 'a'.charCodeAt(0)
    var code_A = 'A'.charCodeAt(0)
    var code_z = 'z'.charCodeAt(0)
    var code_Z = 'Z'.charCodeAt(0)
    var code__ = '_'.charCodeAt(0)

    var containsLowerCaseChar = false
    for (var i=0; i<this._value.length; i++) {
      var c = this._value.charCodeAt(i)
      if (c >= code_a && c <= code_z) {
        containsLowerCaseChar = true
        break
      }
    }

    if (containsLowerCaseChar) {
      var title = this._value[0]

      var lastCharWasLowerCase = false

      for (var i=1; i<this._value.length; i++) {
        var c = this._value.charCodeAt(i)
        if (lastCharWasLowerCase && c>=code_A && c<=code_Z) {
          title = title + ' '
        }
        lastCharWasLowerCase = (c>=code_a && c<=code_z)
        if (c === code__) {
          title = title + ' '
        } else {
          title = title + this._value.charAt(i)
        }
      }
      this._title = title
    } else {
      var title = ''
      var startWord = true
      for (var i=0; i<this._value.length; i++) {
        var c = this._value.charCodeAt(i)
        if (c === code__) {
          title = title + ' '
          startWord = true
        } else {
          if (startWord) {
            title = title + this._value.charAt(i).toUpperCase() 
          } else {
            title = title + this._value.charAt(i).toLowerCase()
          }
          startWord = false
        }
      }
      this._title = title
    }
  },
  
  removePrefix: function(prefixLength) {
    this._title = this._title.substr(prefixLength)
  },
  //@}
})

/** \class MLAB.Core.EnumField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("EnumField", MLAB.Core.Field, {
  EnumField: function() {
    MLAB.Core.EnumField.super.constructor.call(this)
    this._items = []
    this._automaticTitles = {}
  },
  
  isEnumField: function() { return true },
  
  /** \fn MLAB.Core.EnumField.setItems
   * 
   * Sets the enum items.
   * 
   * \param items An array with the enum item strings.
   */
  setItems: function(items) { 
    this._items = items
    this._removeTitlePrefix()
  },
  
  /** \fn MLAB.Core.EnumField.items
   * 
   * Returns the enum items.
   * 
   * \return An array of strings, which are the enum items.  
   */
  items: function() { return this._items },
  
  /** \fn MLAB.Core.EnumField.setCurrentItem
   * 
   * Sets the current enum item.
   * 
   * \param item The item string.
   */
  setCurrentItem: function(item) { this.setValue(item) },
  
  // no conversion necessary, we use only string values
  _valueToString: function(value) { return value },
  _valueFromString: function(value) { return value },
  
  item: function(itemValue) {
    for (var i=0; i<this._items.length; i++) {
      if (this._items[i].value() === itemValue) {
        return this._items[i]
      }
    }
    return null
  },
  
  // TODO: MLABEnumField in MeVisLab removes the title prefix already. It should be send by a message
  // instead of implementing the automatic title creation here.
  //@{
  _removeTitlePrefix: function() {
    // repeat stripping of first word, until all are stripped
    var wordStripped = false
    do {
      var firstWordAndSpace = null
      wordStripped = false
      var item = null
      var i = 0
      
      // search for first entry with autotitle set
      for (; i<this._items.length; i++) {
        item = this._items[i]
        if (item.hasAutoTitle()) {
          i++
          break 
        }
      }
      if (item && item.hasAutoTitle()) {
        // find first space
        var firstSpaceIdx = item.title().indexOf(' ');
        if (firstSpaceIdx>1) {
          // get first word and space
          firstWordAndSpace = item.title().slice(0, firstSpaceIdx+1);
          var foundAutoTitle = false
          var sameTitles = true
          // search in rest of items with autoTitle if they start with same firstWordAndSpace
          for (; i<this._items.length; i++) {
            item = this._items[i]
            if (item.hasAutoTitle()) {
              foundAutoTitle = true
              if (firstWordAndSpace !== item.title().substr(0, firstWordAndSpace.length)) {
                sameTitles = false
                break
              }
            }
          }
          if (foundAutoTitle && sameTitles) {
            // strip first word from all autotitles
            for (var i=0; i<this._items.length; i++) {
              item = this._items[i]
              if (item.hasAutoTitle()) {
                item.removePrefix(firstSpaceIdx+1)
              }
            }
            wordStripped = true
          }
        } 
      }
    } while (wordStripped)
  },
  //@}
})


/** \class MLAB.Core.FloatField(MLAB.Core.NumberField)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("FloatField", MLAB.Core.NumberField, {
  FloatField: function() {
    MLAB.Core.FloatField.super.constructor.call(this)
  },
  
  isFloatField: function() { return true },

  updateValue: function(value) {
    // change double precision to single precision
    var v = MLAB.Core.roundDoubleToFloat(value)
    MLAB.Core.FloatField.super.updateValue.call(this, v)
  },
  
  _valueFromString: function(value) {
    // value is still double precision, but updateValue will reduce it to single precision 
    return parseFloat(value)
  },
})


/** \class MLAB.Core.IntegerField(MLAB.Core.NumberField)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("IntegerField", MLAB.Core.NumberField, {
  IntegerField: function() {
    MLAB.Core.IntegerField.super.constructor.call(this)
  },
  
  isIntegerField: function() { return true },
  
  _valueFromString: function(value) {
    return parseInt(value)
  },
})


/** \class MLAB.Core.MatrixField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("MatrixField", MLAB.Core.Field, {
  MatrixField: function() {
    MLAB.Core.MatrixField.super.constructor.call(this)
  },
  
  isMatrixField: function() { return true },
  
  _valueToString: function(value) {
    // TODO: this needs to be correctly implemented
    return value 
  },
   
  _valueFromString: function(value) {
    // TODO: this needs to be correctly implemented
    return value 
  },
})


/** \class MLAB.Core.StringField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("StringField", MLAB.Core.Field, {
  StringField: function() {
    MLAB.Core.StringField.super.constructor.call(this)
  },
  
  isStringField: function() { return true },
  
  // no conversion necessary
  _valueToString: function(value) { return value },
  _valueFromString: function(value) { return value },
})


/** \class MLAB.Core.TriggerField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("TriggerField", MLAB.Core.Field, {
  TriggerField: function() {
    MLAB.Core.TriggerField.super.constructor.call(this)
  },
  
  isTriggerField: function() { return true },
  
  // trigger fields have no real value
  _valueToString: function(value) { return value },
  _valueFromString: function(value) { return value },
})


/** \class MLAB.Core.VectorField(MLAB.Core.Field)
 * \ingroup Fields
 */
MLAB.Core.deriveClass("VectorField", MLAB.Core.Field, {
  VectorField: function() {
    MLAB.Core.VectorField.super.constructor.call(this)
  },
  
  isVectorField: function() { return true },
  
  _valueToString: function(value) {
    // TODO: this needs to be correctly implemented
    return value 
  },
   
  _valueFromString: function(value) {
    // TODO: this needs to be correctly implemented
    return value
  },
})
