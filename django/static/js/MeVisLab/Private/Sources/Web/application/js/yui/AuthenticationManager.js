/** \class MLAB.YUI.AuthenticationManager(MLAB.GUI.AuthenticationManager)
 * 
 */
MLAB.YUI.deriveClass("AuthenticationManager", MLAB.GUI.AuthenticationManager, {
  AuthenticationManager: function () {
    MLAB.YUI.AuthenticationManager.super.constructor.call(this)
  },
  
  _createLoginDialog: function() {
    var hd = document.createElement("div")
    hd.setAttribute("class", "hd")
    hd.innerHTML = "Login"
    
    var p = document.createElement("p")
    p.innerHTML = "Enter your username and passwort:"
    
    var userLabel  = document.createElement("label")
    userLabel.setAttribute("for", "user")
    userLabel.innerHTML = "Username:"
    var passwordLabel = document.createElement("label")
    passwordLabel.setAttribute("for", "password")
    passwordLabel.innerHTML = "Password:"
    var userInput = document.createElement("input")
    userInput.setAttribute("type", "text")
    userInput.setAttribute("name", "user")
    var passwordInput = document.createElement("input")
    passwordInput.setAttribute("type", "password")
    passwordInput.setAttribute("name", "password")
    
    var table = document.createElement("table")
    var r0 = table.insertRow(0)
    r0.insertCell(0).appendChild(userLabel)
    r0.insertCell(1).appendChild(userInput)
    var r1 = table.insertRow(1)
    r1.insertCell(0).appendChild(passwordLabel)
    r1.insertCell(1).appendChild(passwordInput)
    
    var form = document.createElement("form")
    form.setAttribute("name", "loginDialogForm")
    form.appendChild(p)
    form.appendChild(table)
    
    var bd = document.createElement("div")
    bd.setAttribute("class", "bd")
    bd.appendChild(form)
    
    this._loginDialog = document.createElement("div")
    this._loginDialog.id = "loginDialog"
    this._loginDialog.appendChild(hd)
    this._loginDialog.appendChild(bd)
    document.body.appendChild(this._loginDialog)

    var handleSubmit = function() {
      this._yuiLoginDialog.hide()
      this.setAuthentication(userInput.value, MLAB['Core'].encodeBase64(passwordInput.value))
      this.authenticateModuleContexts()
      passwordInput.value = ""
    }
    
    this._yuiLoginDialog = new YAHOO.widget.Dialog("loginDialog", { 
       width : "25em",
       fixedcenter : true,
       visible : false, 
       constraintoviewport : true,
       buttons : [ { text:"Login", handler:handleSubmit.bind(this), isDefault:true },
                   { text:"Cancel", handler: (function(){this._yuiLoginDialog.hide()}).bind(this) } ]
    })
    
    var enterKeyListener = new YAHOO.util.KeyListener(document, { keys:13 },
        { fn:handleSubmit, scope:this._yuiLoginDialog, correctScope:true }, 
        "keyup")
    this._yuiLoginDialog.cfg.queueProperty("keylisteners", enterKeyListener)
    
    this._yuiLoginDialog.render()
  },
  
  requestAuthentication: function() {    
    if (!this._loginDialog) {
      this._createLoginDialog()
    }
    this._yuiLoginDialog.show()
  },
})
