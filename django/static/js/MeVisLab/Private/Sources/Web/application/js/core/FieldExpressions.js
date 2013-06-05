/**
 * Attempts to implement the same type conversion logic as QVariant.
 */
MLAB.Core.defineClass("FieldExpressionValue", {
  FieldExpressionValue: function() {
    this._isRegExp = false
    this._isBool = false
    this._isNumber = false
    this._isString = false
    this._value = null
  },
  
  setBoolValue:   function(value) { this._value = value; this._isBool   = true },
  setNumberValue: function(value) { this._value = value; this._isNumber = true },
  setStringValue: function(value) { this._value = value; this._isString = true },
  setRegExpValue: function(value) { this._value = value; this._isRegExp = true },
  
  isBool:   function() { return this._isBool   },
  isNumber: function() { return this._isNumber },
  isString: function() { return this._isString },
  isRegExp: function() { return this._isRegExp },
  
  toBool: function() { 
    if (this._isBool) { 
      return this._value
    } else if (this._isNumber) { 
      return this._value !== 0
    } else if (this._isString) {
      return this._value.length > 0 && this._value !== "0" && this._value.toLowerCase() !== "false" 
    } 
    return false
  },
  
  toNumber: function() {
    return Number(this._value)
  },
  
  toString: function() {
    var s = "<Invalid FieldExpressionValue>"
    if (this._value !== null) {
      s = this._value.toString()
    }
    return s
  },

  toRegExp: function() {
    if (this._isRegExp) {
      return this._value
    } else {
      return undefined
    }
  }
})

MLAB.Core.defineClass("FieldExpressionNode", {
  FieldExpressionNode: function() {
    this._negate = false
  },
  
  setNegate: function(negate) { this._negate = negate },
  
  toggleNegate: function() { this._negate = !this._negate },
  
  evaluate: function() {
    var r = this._exec()
    if (this._negate) { r.setBoolValue(!r.toBool()) }
    return r
  },
  
  _exec: function() { MLAB.Core.throwException("_exec() is not implemented") },
})



MLAB.Core.deriveClass("FieldExpBinaryNode", MLAB.Core.FieldExpressionNode, {
  FieldExpBinaryNode: function(left, right) {
    MLAB.Core.FieldExpBinaryNode.super.constructor.call(this)
    this._left = left
    this._right = right
  },
})

MLAB.Core.deriveClass("FieldExpEqualsNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpEqualsNode: function(negate, left, right) {
    MLAB.Core.FieldExpEqualsNode.super.constructor.call(this, left, right)
    this._negate = negate
  },

  _exec: function() {
    var result = new MLAB.Core.FieldExpressionValue()
    if (this._left && this._right) {
      var l = this._left.evaluate()
      var r = this._right.evaluate()
      if (l.isBool()) {
        result.setBoolValue(l.toBool() === r.toBool()) 
      } else {
        var lNumber = l.toNumber()
        var rNumber = r.toNumber()
        if (!isNaN(lNumber) && !isNaN(rNumber)) {
          var eps = Math.max(Math.abs(lNumber), Math.abs(rNumber)) * 1e-6
          result.setBoolValue(Math.abs(lNumber - rNumber) < eps)
        } else if (r.isRegExp()) {
          if (r.toRegExp().test(l.toString())) { result.setBoolValue(true) }
        } else {
          result.setBoolValue(l.toString() === r.toString())
        }
      }
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpCompareNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpCompareNode: function(less, negate, left, right) {
    MLAB.Core.FieldExpCompareNode.super.constructor.call(this, left, right)
    this._less = less
    this._negate = negate
  },

  _exec: function() {
    var result = new MLAB.Core.FieldExpressionValue()
    if (this._left && this._right) {
      var l = this._left.evaluate()
      var r = this._right.evaluate()
      var lNumber = l.toNumber()
      var rNumber = r.toNumber()
      if (!isNaN(lNumber) && !isNaN(rNumber)) {
        if (this._less) {
          result.setBoolValue(lNumber < rNumber)
        } else {
          result.setBoolValue(lNumber > rNumber)
        }
      } else {
        if (this._less) {
          result.setBoolValue(l.toString() < r.toString())
        } else {
          result.setBoolValue(l.toString() > r.toString())
        }
      }
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpAndNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpAndNode: function(left, right) {
    MLAB.Core.FieldExpAndNode.super.constructor.call(this, left, right)
  },
  
  _exec: function() {
    var result
    if (this._left && this._right) {
      result = this._left.evaluate()
      if (result.toBool()) {
        result = this._right.evaluate()
      }
    } else {
      result = new MLAB.Core.FieldExpressionValue()
    }
    return result
  },
})
  
MLAB.Core.deriveClass("FieldExpOrNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpOrNode: function(left, right) {
    MLAB.Core.FieldExpOrNode.super.constructor.call(this, left, right)
  },
  
  _exec: function() {
    var result
    if (this._left && this._right) {
      result = this._left.evaluate()
      if (!result.toBool()) { 
        result = this._right.evaluate()
      }
    } else {
      result = new MLAB.Core.FieldExpressionValue()
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpPlusNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpPlusNode: function(left, right) {
    MLAB.Core.FieldExpPlusNode.super.constructor.call(this, left, right)
  },
  
  _exec: function() {
    var result = new MLAB.Core.FieldExpressionValue()
    if (this._left && this._right) {
      var l = this._left.evaluate()
      var r = this._right.evaluate()
      var lNumber = l.toNumber()
      var rNumber = r.toNumber()
      if (!isNaN(lNumber) && !isNaN(rNumber)) {
        result.setNumberValue(lNumber + rNumber)
      } else {
        result.setStringValue(l.toString() + r.toString())
      }
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpMinusNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpMinusNode: function(left, right) {
    MLAB.Core.FieldExpMinusNode.super.constructor.call(this, left, right)
  },
  
  _exec: function() {
    var result = new MLAB.Core.FieldExpressionValue()
    if (this._left && this._right) {
      var l = this._left.evaluate()
      var r = this._right.evaluate()
      var lNumber = l.toNumber()
      var rNumber = r.toNumber()
      if (!isNaN(lNumber) && !isNaN(rNumber)) {
        result.setNumberValue(lNumber - rNumber)
      } else {
        result.setStringValue(l.toString().replace(r.toString(), ""))
      }
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpMultiplyNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpMultiplyNode: function(left, right) {
    MLAB.Core.FieldExpMultiplyNode.super.constructor.call(this, left, right)
  },
  
  _exec: function() {
    var result = new MLAB.Core.FieldExpressionValue()
    if (this._left && this._right) {
      var l = this._left.evaluate()
      var r = this._right.evaluate()
      var lNumber = l.toNumber()
      var rNumber = r.toNumber()
      if (!isNaN(lNumber) && !isNaN(rNumber)) {
        result.setNumberValue(lNumber * rNumber)
      }
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpDivideNode", MLAB.Core.FieldExpBinaryNode, {
  FieldExpDivideNode: function(left, right) {
    MLAB.Core.FieldExpDivideNode.super.constructor.call(this, left, right)
  },
  
  _exec: function() {
    var result = new MLAB.Core.FieldExpressionValue()
    if (this._left && this._right) {
      var l = this._left.evaluate()
      var r = this._right.evaluate()
      var lNumber = l.toNumber()
      var rNumber = r.toNumber()
      if (!isNaN(lNumber) && !isNaN(rNumber)) {
        result.setNumberValue(lNumber / rNumber)
      }
    }
    return result
  },
})

MLAB.Core.deriveClass("FieldExpFieldValueNode", MLAB.Core.FieldExpressionNode, {
  FieldExpFieldValueNode: function(field) {
    MLAB.Core.FieldExpFieldValueNode.super.constructor.call(this)
    this._field = field
  },
    
  _exec: function() {
    var v = new MLAB.Core.FieldExpressionValue()
    if (this._field.isBoolField()) {
      v.setBoolValue(this._field.getValue())
    } else if (this._field.isNumberField()) {
      v.setNumberValue(this._field.getValue())
    } else {
      v.setStringValue(this._field.stringValue())
    }
    return v
  },
})

MLAB.Core.deriveClass("FieldExpNumberValueNode", MLAB.Core.FieldExpressionNode, {
  FieldExpNumberValueNode: function(numberValue) {
    MLAB.Core.FieldExpNumberValueNode.super.constructor.call(this)
    this._value = numberValue
  },
  
  _exec: function() { 
    var v = new MLAB.Core.FieldExpressionValue()
    v.setNumberValue(this._value)
    return v
  },
})

MLAB.Core.deriveClass("FieldExpStringValueNode", MLAB.Core.FieldExpressionNode, {
  FieldExpStringValueNode: function(stringValue) {
    MLAB.Core.FieldExpStringValueNode.super.constructor.call(this)
    this._value = stringValue
  },
  
  _exec: function() { 
    var v = new MLAB.Core.FieldExpressionValue()
    v.setStringValue(this._value)
    return v
  },
})

MLAB.Core.deriveClass("FieldExpRegExpNode", MLAB.Core.FieldExpressionNode, {
  FieldExpRegExpNode: function(regExpString) {
    MLAB.Core.FieldExpRegExpNode.super.constructor.call(this)
    this._regExp = null
    this._setup(regExpString)
  },
  
  _setup: function(regExpString) {
    if (regExpString.charAt(regExpString.length-1) === "i") {
      this._value = new RegExp(regExpString.slice(1,regExpString.length-2), 'i')
    } else {
      this._value = new RegExp(regExpString.slice(1,regExpString.length-1))
    }
  },
  
  _exec: function() { 
    var v = new MLAB.Core.FieldExpressionValue()
    v.setRegExpValue(this._value)
    return v
  },
})


MLAB.Core.defineClass("FieldExpressionTokenizer", {
  FieldExpressionTokenizer: function(expression) {
    this._data = expression
    this._pos = 0
    this._putback = false
    this._length = this._data.length
    this._currentToken = null
    this._currentValue = null
    this._currentNumber = NaN
    
    // tokens
    this.LogicalOr = 0
    this.LogicalAnd = 1
    this.Equals = 2
    this.EqualsNot = 3
    this.Less = 4
    this.LessEqual = 5
    this.Greater = 6
    this.GreaterEqual = 7
    this.Plus = 8
    this.Minus = 9
    this.Multiply = 10
    this.Divide = 11
    this.Number = 12
    this.String = 13
    this.Field = 14
    this.OpenBrace = 15
    this.CloseBrace = 16
    this.Negate = 17
    this.EndOfFile = 18
    this.RegExp = 19
  },

  skipWhiteSpace: function() {
    while (this._pos<this._length) {
      if (this._data[this._pos] !== " " && 
          this._data[this._pos] !== "\n" && 
          this._data[this._pos] !== "\t") {
        break 
      }
      this._pos++
    }
  },

  nextToken: function() {
    if (this._putback) {
      this._putback = false
      return this._currentToken
    }
    if (this._pos >= this._length) {
      this._currentToken = this.EndOfFile
      return this._currentToken
    }
    
    this.skipWhiteSpace()
  
    var current = this._data[this._pos]
    var next = (this._pos+1 < this._length) ? this._data[this._pos+1] : "\0"
    if (current==='|') {
      if (next==='|') {
        this._pos+=2
        this._currentToken = this.LogicalOr
        return this._currentToken
      }
    }
    if (current==='&') {
      if (next==='&') {
        this._pos+=2
        this._currentToken = this.LogicalAnd
        return this._currentToken
      }
    }
    if (current==='=') {
      if (next==='=') {
        this._pos+=2
        this._currentToken = this.Equals
        return this._currentToken
      }
    }
    if (current==='(') {
      this._pos+=1
      this._currentToken = this.OpenBrace
      return this._currentToken
    }
    if (current===')') {
      this._pos+=1
      this._currentToken = this.CloseBrace
      return this._currentToken
    }
    if (current==='+') {
      this._pos+=1;
      this._currentToken = this.Plus;
      return this._currentToken;
    }
    if (current==='-') {
      this._pos+=1;
      this._currentToken = this.Minus;
      return this._currentToken;
    }
    if (current==='*') {
      this._pos+=1;
      this._currentToken = this.Multiply;
      return this._currentToken;
    }
    if (current==='!') {
      if (next==='=') {
        this._pos+=2
        this._currentToken = this.EqualsNot
        return this._currentToken
      }
      this._pos+=1
      this._currentToken = this.Negate
      return this._currentToken
    }
    if (current==='<') {
      if (next==='=') {
        this._pos+=2;
        this._currentToken = this.LessEqual;
        return this._currentToken;
      } else {
        this._pos+=1;
        this._currentToken = this.Less;
        return this._currentToken;
      }
    }
    if (current==='>') {
      if (next==='=') {
        this._pos+=2;
        this._currentToken = this.GreaterEqual;
        return this._currentToken;
      } else {
        this._pos+=1;
        this._currentToken = this.Greater;
        return this._currentToken;
      }
    }
    if (current==='"' || current==='\'' || current==='/') {
      var delimiter = current
      if (delimiter === '/') {
        this._currentToken = this.RegExp
      } else {
        this._currentToken = this.String
      }
      // find closing " or ', no escaping of " or ' allowed at the moment
      var i = this._data.indexOf(delimiter,this._pos+1)
      if (i===-1 || i>this._length) {
        i = this._length
      }
      if (this._currentToken === this.RegExp) {
        // on a regexp, we return /.../i as the token
        if (this._data[i+1]==='i') {
          i++;
        }
        this._currentValue = this._data.slice(this._pos,i+1)
      } else {
        // on strings, we cut the leading/trailing " or '
        this._currentValue = this._data.slice(this._pos+1,i)
      }
      this._pos = i+1
      return this._currentToken
    }
  
    // find end of field name
    var i = this._pos+1
    while (i<this._length) {
      var c = this._data[i]      
      var charCode = c.charCodeAt(0)      
      if (!MLAB.Core.isLetterOrNumber(charCode) && c!='_' && c!='.' && c!=':') { 
        break 
      }
      i++
    }
    this._currentValue = this._data.slice(this._pos,i)
    this._currentNumber = Number(this._currentValue)
    if (isNaN(this._currentNumber)) {
      this._currentToken = this.Field
    } else {
      this._currentToken = this.Number
    }
    if (this._currentValue.length === 0 && i>=this._length) {
      this._currentToken = this.EndOfFile
    }
    this._pos = i
    return this._currentToken
  },
  
  debugToken: function() {
    switch(this._currentToken) {
      case this.Equals:        return "=="
      case this.EqualsNot:     return "!="
      case this.Less:          return "<"
      case this.LessEqual:     return "<="
      case this.Greater:       return ">"
      case this.GreaterEqual:  return ">="
      case this.LogicalOr:     return "||"
      case this.LogicalAnd:    return "&&"
      case this.Plus:          return "+"
      case this.Minus:         return "-"
      case this.Multiply:      return "*"
      case this.Divide:        return "/"
      case this.Number:        return this.currentNumber().toString()
      case this.String:        return "String(" + this.currentValue() + ")"
      case this.Field:         return "Field(" + this.currentValue() + ")"
      case this.OpenBrace:     return "("
      case this.CloseBrace:    return ")"
      case this.EndOfFile:     return "EndOfFile"
      case this.Negate:        return "!"
      case this.RegExp:        return "RegExp(" + this.currentValue() + ")"
    }
    return "Unknown"
  },
  
  currentValue: function() { return this._currentValue },
  
  currentNumber: function() { return this._currentNumber },
  
  putBack: function() { this._putback = true },
  
  currentToken: function() { return this._currentToken },
})

/** \class MLAB.Core.FieldExpressionParser
 */
MLAB.Core.defineClass("FieldExpressionParser", {
  FieldExpressionParser: function(owner, module) {
    this._module = module
    this._owner = owner
  },
  
  parseExpression: function(expression) {
    var tokenizer = new MLAB.Core.FieldExpressionTokenizer(expression)
    var expression = this._createOrExpression(tokenizer)
    if (tokenizer.nextToken() != tokenizer.EndOfFile) {
      // final error if not reached end of expression
      this._module.logError("FieldExpressionParser: unexpected token " + tokenizer.debugToken())
    }
    return expression
  },
  
  _createOrExpression: function(tokenizer) {
    var right = null
    var left = this._createAndExpression(tokenizer)
    if (!left)  { return null }
    while (true) {
      var token = tokenizer.nextToken()
      if (token === tokenizer.LogicalOr) {
        right = this._createAndExpression(tokenizer)
        if (left && right) {
          left = new MLAB.Core.FieldExpOrNode(left, right)
        } else {
          this._module.logError("FieldExpressionParser: missing statement after ||")
          return null
        }
      } else {
        tokenizer.putBack()
        return left
      }
    }
  },

  _createAndExpression: function(tokenizer) {
    var right = null
    var left = this._createComparison(tokenizer)
    if (!left)  { return null }
    while (true) {
      var token = tokenizer.nextToken()
      if (token === tokenizer.LogicalAnd) {
        right = this._createComparison(tokenizer)
        if (left && right) {
          left = new MLAB.Core.FieldExpAndNode(left, right)
        } else {
          this._module.logError("FieldExpressionParser: missing statement after &&")
          return null
        }
      } else {
        tokenizer.putBack()
        return left
      }
    }
  },

  _createComparison: function(tokenizer) {
    var left = this._createPlusMinus(tokenizer)
    if (!left) { return null }

    var token = tokenizer.nextToken()
    var tokenRepr = tokenizer.debugToken();
    if (token == tokenizer.Equals  || token == tokenizer.EqualsNot ||
        token == tokenizer.Less    || token == tokenizer.LessEqual ||
        token == tokenizer.Greater || token == tokenizer.GreaterEqual)
    {
      var right = this._createPlusMinus(tokenizer)
      if (left && right) {
        switch(token) {
        case tokenizer.Equals:
          return new MLAB.Core.FieldExpEqualsNode(false, left, right)
        case tokenizer.EqualsNot:
          return new MLAB.Core.FieldExpEqualsNode(true, left, right)
        case tokenizer.Less:
          return new MLAB.Core.FieldExpCompareNode(true, false, left, right)
        case tokenizer.LessEqual:
          return new MLAB.Core.FieldExpCompareNode(false, true, left, right)
        case tokenizer.Greater:
          return new MLAB.Core.FieldExpCompareNode(false, false, left, right)
        case tokenizer.GreaterEqual:
          return new MLAB.Core.FieldExpCompareNode(true, true, left, right)
        default:
          this._module.logError("FieldExpressionParser: unhandled comparison operator")
          return null
        }
      } else {
        this._module.logError("FieldExpressionParser: missing statement after " + tokenRepr)
        return null
      }
    } else {
      tokenizer.putBack()
      return left
    }
  },

  _createPlusMinus: function(tokenizer) {
    var right = null
    var left = this._createMultDiv(tokenizer)
    if (!left)  { return null }
    while (true) {
      var token = tokenizer.nextToken()
      if (token === tokenizer.Plus) {
        right = this._createMultDiv(tokenizer)
        if (left && right) {
          left = new MLAB.Core.FieldExpPlusNode(left, right)
        } else {
          this._module.logError("FieldExpressionParser: missing statement after +")
          return null
        }
      } else if (token === tokenizer.Minus) {
        right = this._createMultDiv(tokenizer)
        if (left && right) {
          left = new MLAB.Core.FieldExpMinusNode(left, right)
        } else {
          this._module.logError("FieldExpressionParser: missing statement after -")
          return null
        }
      } else {
        tokenizer.putBack()
        return left
      }
    }
  },
  
  _createMultDiv: function(tokenizer) {
    var right = null
    var left = this._createBrace(tokenizer)
    if (!left)  { return null }
    while (true) {
      var token = tokenizer.nextToken()
      if (token === tokenizer.Multiply) {
        right = this._createBrace(tokenizer)
        if (left && right) {
          left = new MLAB.Core.FieldExpMultiplyNode(left, right)
        } else {
          this._module.logError("FieldExpressionParser: missing statement after *")
          return null
        }
      } else if (token === tokenizer.Divide) {
        right = this._createBrace(tokenizer)
        if (left && right) {
          left = new MLAB.Core.FieldExpDivideNode(left, right)
        } else {
          this._module.logError("FieldExpressionParser: missing statement after /")
          return null
        }
      } else {
        tokenizer.putBack()
        return left
      }
    }
  },

  _createBrace: function(tokenizer) {
    var token = tokenizer.nextToken()
    var negate = false
    var unaryMinus = false
    // only one of unary minus or unary not should be applicable
    if (token == tokenizer.Minus) {
      unaryMinus = true
      token = tokenizer.nextToken()
    } else if (token === tokenizer.Negate) {
      negate = true
      token = tokenizer.nextToken()
    }
    var result = null
    if (token === tokenizer.OpenBrace) {
      result = this._createOrExpression(tokenizer)
      if (!result) {
        this._module.logError("FieldExpressionParser: missing expression after (")
      } else {
        if (negate) {
          result.toggleNegate()
        }
      }
      token = tokenizer.nextToken()
      if (token !== tokenizer.CloseBrace) {
        this._module.logError("FieldExpressionParser: missing close brace")
        return NULL
      }
    } else {
      tokenizer.putBack()
      result = this._createSimple(tokenizer, negate)
    }
    if (unaryMinus) {
      // represent unary minus by 0 - node
      result = new MLAB.Core.FieldExpMinusNode(new MLAB.Core.FieldExpNumberValueNode(0), result);
    }
    return result
  },

  _createSimple: function(tokenizer, negate) {
    var token = tokenizer.nextToken()
    if (token === tokenizer.Negate) {
      negate = !negate
      token = tokenizer.nextToken()
    }
    var node = this._createNode(token, tokenizer, negate)
    if (!node) {
      this._module.logError("FieldExpressionParser: unexpected token " + tokenizer.debugToken())
    }
    return node
  },
  
  _createNode: function(token, tokenizer, negate) {
    var r = null
    if (token == tokenizer.Field) {
      var field = this._module.field(tokenizer.currentValue());
      if (field) {
        r = new MLAB.Core.FieldExpFieldValueNode(field)
        r.setNegate(negate)
        this._owner.addDependencyField(field)
      } else {
        this._module.logError("FieldExpressionParser: field not found " + tokenizer.currentValue())
      }
  
    } else if (token == tokenizer.Number) {
      r = new MLAB.Core.FieldExpNumberValueNode(tokenizer.currentNumber())
    } else if (token == tokenizer.String) {
      r = new MLAB.Core.FieldExpStringValueNode(tokenizer.currentValue())
      r.setNegate(negate)
    } else if (token == tokenizer.RegExp) {
      r = new MLAB.Core.FieldExpRegExpNode(tokenizer.currentValue())
    }
    return r
  },
})


/** \class MLAB.Core.FieldExpressionEvaluator(MLAB.Core.Object)
 * 
 */
MLAB.Core.deriveClass("FieldExpressionEvaluator", MLAB.Core.Object, {
  FieldExpressionEvaluator: function(expression, module) {
    MLAB.Core.FieldExpressionEvaluator.super.constructor.call(this)
    this.registerSignal("resultChanged")
    this._module = module
    this._dependencyFields = []
    this._expression = (new MLAB.Core.FieldExpressionParser(this, module)).parseExpression(expression)
  },
  
  /** \fn MLAB.Core.FieldExpressionEvaluator.addDependencyField
   * 
   * Adds a dependency field that causes reevaluate.
   */
  addDependencyField: function(field) {
    this._dependencyFields.push(field)
    field.addListener(this)
  },
  
  destroy: function() {
    for (var i=0; i<this._dependencyFields.length; i++) {
      this._dependencyFields.removeListener(this)
    }
  },
  
  fieldChanged: function() { 
    this._evaluate() 
  },
  
  _evaluate: function() {
    if (this._expression) {
      var r = this._expression.evaluate()
      this.emit("resultChanged", r.toBool(), r)
    }
  }
})

