var gDemoDataFilesByDirectory = {};


//=============================================================================
// demoInitialize() - code entry for the demo application
// (it is called from demo.html)
//=============================================================================
function demoInitialize() {
  document.title = "Visia";
  // create the demo instance
  var demo = new Demo();
  demo.init();
  // register the callback that is called when all module contexts are created
  gApp.setModuleContextsReadyCallback(demo.moduleContextsReady);
}


//=============================================================================
// The Demo class
//=============================================================================
function Demo() {
  var self = this;
  
  
  //=============================================================================
  // init() - prepares the divs for the module panels and the demo data browser
  //=============================================================================
  this.init = function() {
    gApp.showLoadDialog();

    // create layouting elements    
    var bodyTable = document.createElement("table");    
    bodyTable.setAttribute("class", "bodyTable");
    gApp.body.appendChild(bodyTable);
    var bodyRow = bodyTable.insertRow(0);
    
    var mainTable = document.createElement("table");    
    mainTable.setAttribute("class", "mainTable");
    bodyRow.insertCell(0).appendChild(mainTable);
        
    var panelDiv = document.createElement("div");
    panelDiv.setAttribute("class", "panelDiv");
    mainTable.insertRow(0).insertCell(0).appendChild(panelDiv);
    
    self.imageListDiv = document.createElement("div");
    panelDiv.appendChild(self.imageListDiv);
     
    // create and add the DemoWebApplication module panel
    // - the first parameter must be the exact name of the macro module that will
    //   be instantiated on the server
    // - the second parameter can be any id that is unique in the html document
    var isLoginRequired = true;
    var moduleContextDiv = gApp.createModuleContextDiv("MeVisAPDemoWebApp", "MeVisAPDemoModulePanelDiv", isLoginRequired);
    panelDiv.appendChild(moduleContextDiv);

    var viewersDiv = document.createElement("div");
    viewersDiv.id = "Window_Viewers";
    
    var viewersTable = document.createElement("table");
    viewersTable.insertRow(0).insertCell(0).appendChild(viewersDiv);
    
    var helpDialogDiv = document.createElement("div");
    helpDialogDiv.id = "helpDialogDiv";
    document.body.appendChild(helpDialogDiv);
    self.helpDialog = new YAHOO.widget.Panel(helpDialogDiv.id,   
                                             { width:"260px",  
                                               fixedcenter:true,  
                                               close:true,  
                                               draggable:true,  
                                               zindex:4, 
                                               modal:false, 
                                               visible:false 
                                             });
    self.helpDialog.setHeader("Help");
    self.helpDialog.setBody('<div class="helpSection">The side panel on the left lets you select a study. If it is loaded, ' +
                            'then its images will be displayed. For each image there is a checkbox to ' +
                            'select it as an overlay. The anatomical images have a second checkbox to select them ' +
                            'as the underlay.</div>' +
                            '<div class="helpSection">The viewer interaction differs from the Visia viewers, because they are ' +
                            'MeVisLab viewers. The middle mouse button action is already predefined by most ' +
                            'browsers, so we are using the left mouse button (LMB) and a key as a replacement.</div>' +
                            '<div class="helpSection">You can zoom in the 3D viewer by pressing Ctrl+LMB and ' + 
                            'moving the mouse forward and backward. The scene will be translated when you press ' +
                            'Shift+LMB and move the mouse.</div>' +
                            '<div class="helpSection">The right mouse button is used for windowing in the 2D viewers. ' +
                            'The cutlines can be moved and rotated by dragging with the LMB. If the middle mouse button ' +
                            'is usable in your browser, then you can zoom in the 2D viewers by pressing it and the Ctrl key ' + 
                            'and moving the mouse.</div>'); 
    self.helpDialog.render(document.body);
    
    var helpLink = document.createElement("a");
    helpLink.innerHTML = "Help";
    helpLink.setAttribute("class", "helpLink");
    helpLink.onclick = function() {
      self.helpDialog.show();
    };
    var helpDiv = document.createElement("div");
    helpDiv.setAttribute("class", "helpDiv");
    helpDiv.appendChild(helpLink);
    viewersTable.insertRow(0).insertCell(0).appendChild(helpDiv);

    var sidepanelDiv = document.createElement("div");
    sidepanelDiv.id = "Window_Sidepanel";
    
    var table = document.createElement("table");
    var row = table.insertRow(0);
    row.insertCell(0).appendChild(viewersTable);
    row.insertCell(0).appendChild(sidepanelDiv);
    moduleContextDiv.appendChild(table);
    
    function createLogo() {
      var url = window.location.protocol + "//" + window.location.host + "/Packages/Visia/EnterpriseApp/Resources/Images/Branding/BackgroundLogo.png";
      var img = document.createElement("img");
      img.src = url;
      var tr = viewersTable.insertRow(2);
      tr.setAttribute("class", "logo");
      var c = tr.insertCell(0);
      c.appendChild(img);
    }
    //createLogo();
    
    // create a div for diagnosis messages
    function createDiagnosisPanel() {
      var t = document.createElement("table");
      t.setAttribute("class", "diagnosisTable");
      var c = bodyTable.insertRow(1).insertCell(0);
      c.setAttribute("colspan", "2");
      c.appendChild(t);
      
      var div = document.createElement("div");
      div.setAttribute("class", "diagnosisDiv");    
      var contentDiv = document.createElement("div"); 
      contentDiv.setAttribute("class", "diagnosisContentDiv");
      contentDiv.id = "DiagnosisPanel";
      div.appendChild(contentDiv);
      t.insertRow(0).insertCell(0).appendChild(div);
      
      var titleDiv = document.createElement("div");
      titleDiv.setAttribute("class", "captionDiv");
      titleDiv.innerHTML = "Diagnosis Console";
      t.insertRow(0).insertCell(0).appendChild(titleDiv);
    }
    
    if (gApp.showDiagnosisPanel()) {
      createDiagnosisPanel();
    }
  };

  
  //=============================================================================
  // moduleContextsReady() - this is registered as callback in the application
  // after all module contexts haven been created
  //=============================================================================
  this.moduleContextsReady = function () {
    if ("rotorOn" in gApp.getArguments()) {
      gApp.getModuleContext("MeVisAPDemoModulePanelDiv").getModule().setFieldValue("rotorOn", "true");
    }
    // hide the load dialog
    gApp.hideLoadDialog();
  };
}
