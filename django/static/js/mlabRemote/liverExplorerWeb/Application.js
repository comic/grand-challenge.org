
//=============================================================================
// liverExplorerInitialize() - code entry for the demo application
// (it is called from liverExplorerWeb.html)
//=============================================================================
function liverExplorerInitialize() {
  document.title = "Liver Explorer Web Application";
  // create the demo instance
  var app = new LiverExplorer();
  //app.init();
  // register the callback that is called when all module contexts are created
  gApp.setModuleContextsReadyCallback(app.moduleContextsReady);
}


//=============================================================================
// The Demo class
//=============================================================================
function LiverExplorer() {
  var self = this;
  
  gApp.loadWEMasJSON = function(loadCallback) {
    ctx = gApp.getModuleContext("RemoteLiverExplorerDiv");
    ctx.sendGenericRequest("getWEMasJSON", [], function(arguments) {
      try {
        var json = arguments[0];
        loadCallback(JSON.parse(json));
      } catch (e) {
        gApp.logError("Failed to load wem, see exception below.");
        gApp.logException(e);
      }
    });
  }  
  gApp.loadPatients = function() {
    ctx = gApp.getModuleContext("RemoteLiverExplorerDiv");
    ctx.sendGenericRequest("getPatients", [], function(arguments) {
      try {
        var json = arguments[0];
        $("div[data-role=content] .listcontainer").html(json).trigger("create");
        //self.patients = JSON.parse(json);
        
      } catch (e) {
        gApp.logError("Failed to load patients, see exception below.");
        gApp.logException(e);
      }
    });
  }  
  gApp.loadPatient = function(uid) {
    ctx = gApp.getModuleContext("RemoteLiverExplorerDiv");
    ctx.sendGenericRequest("loadPatient", [uid], function(arguments) {
     // $.mobile.changePage( $("#appWindow"), { transition: "slideup"} );
    });
  }
  //=============================================================================
  // init() - prepares the divs for the module panels and the demo data browser
  //=============================================================================
  this.init = function() {
    gApp.showLoadDialog();
    console.log("Init liver app");
    
    // create a function to add further module panels to the page
    function createCommonModulePanel(moduleName, bodyTableRowIdx, title, description, descriptionIsLeft) {
      var table = document.createElement("table");
      table.setAttribute("class", "commonModuleTable");
      
      var titleDiv = document.createElement("div");
      titleDiv.setAttribute("class", "captionDiv");
      titleDiv.innerHTML = title;
      table.insertRow(0).insertCell(0).appendChild(titleDiv);
      
      var div = gApp.createModuleContextDiv(moduleName, moduleName + "PanelDiv");
      table.insertRow(1).insertCell(0).appendChild(div);
            
      var bodyTableRow = bodyTable.insertRow(bodyTableRowIdx);      
      var cell0 = bodyTableRow.insertCell(0);
      cell0.setAttribute("class", "bodyTable");
      
      var descriptionDiv = document.createElement("div");
      
      if (descriptionIsLeft) {
        descriptionDiv.setAttribute("class", "commonDescriptionDiv leftDescriptionDiv");
        descriptionDiv.innerHTML = description;
        var t = document.createElement("table");
        var r = t.insertRow(0);
        var c0 = r.insertCell(0);
        c0.setAttribute("class", "commonDescriptionDiv leftDescriptionCell");
        c0.appendChild(descriptionDiv);
        r.insertCell(1).appendChild(table);
        cell0.setAttribute("colspan", "2");
        cell0.appendChild(t);
      } else {
        descriptionDiv.setAttribute("class", "commonDescriptionDiv descriptionDiv");
        descriptionDiv.innerHTML = description;
        cell0.appendChild(table);
        
        var cell1 = bodyTableRow.insertCell(1);
        cell1.setAttribute("class", "bodyTable");
        cell1.appendChild(descriptionDiv);
      }
    }
    
    createCommonModulePanel("RemoteRenderingCSOExampleModule", 1, 
                            "CSO Rendering Example", 
                            "The viewers to the right are the remotely rendered output of the " +
                            "<i>RemoteRenderingCSOExampleModule</i> module. " +
                            "It is possible to draw a contour in the left viewer.", 
                            true);
    
    // create a div for diagnosis messages
    function createDiagnosisPanel() {
      var t = document.createElement("table");
      t.setAttribute("class", "diagnosisTable");
      var c = bodyTable.insertRow(2).insertCell(0);
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
    // create the demo data browser
    //self.createDemoDataBrowser();
    
    //var moduleContext = gApp.getModuleContext("DemoModulePanelDiv");
    //moduleContext.sendMessage(m);
    
    // hide the load dialog
    //gApp.hideLoadDialog();
    console.log("module loaded");
    gApp.loadPatients();
    //$('#patients').html("modules loaded");
    initWebGL();
    animate();

  };
  
  
  //=============================================================================
  // loadDemoDataFiles() - loads the files for a directory node
  //=============================================================================
  this.loadDemoDataFiles = function(node, callback) {
    var tmpNode = node;
    
    try {
      function responseHandler(result) {
        try {
          if (result && (result.length == 1) && result[0]) {
            tmpNode.files = result[0];
          } else {
            tmpNode.files = [];
          }
          callback(tmpNode);
        } catch (e) {
          gApp.logException(e);
        }
      }
      
      var functionName = "handleDemoDataFilesRequest"
      var arguments = [self.getDirectoryFromNode(node)];
      
      // send a generic request to the macro module on the server to ask for
      // the files of the current node
      var moduleContext = gApp.getModuleContext("DemoModulePanelDiv");
      moduleContext.sendGenericRequest(functionName, arguments, 
                                       function(result) { responseHandler(result, node); } );
    } catch (e) {
      gApp.logException(e);
    }
  }
  
  
  //=============================================================================
  // createDemoDataBrowser()
  //=============================================================================
  this.createDemoDataBrowser = function() {
    
    //--------------------------------------------------
    // create the yui data table that will contain the 
    // files of the selected directory
    //--------------------------------------------------
    var fileListTableDiv = document.createElement("div");
    fileListTableDiv.id = "fileListTable";
    self.demoDataBrowserElement.insertCell(0).appendChild(fileListTableDiv);
    
    var fileListDataSource = new YAHOO.util.DataSource({});
    fileListDataSource.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
    fileListDataSource.responseSchema = { fields: ["Name", "Path"] };
  
    self.fileListTable = new YAHOO.widget.DataTable("fileListTable", 
                                                   [{key: "Path", label: "Path", hidden:true},
                                                    {key: "Name", label: "File", sortable:true}],
                                                   fileListDataSource,
                                                   {scrollable: true, height: "10em"}); 
    self.fileListTable.subscribe("rowMouseoverEvent", self.fileListTable.onEventHighlightRow);
    self.fileListTable.subscribe("rowMouseoutEvent", self.fileListTable.onEventUnhighlightRow);
    self.fileListTable.subscribe("rowClickEvent", self.handleTableRowSelected);


    // create a div into which the demo data tree view will be placed
    var demoDataTreeDiv = document.createElement("div");
    demoDataTreeDiv.id = "demoDataTreeDiv";
    self.demoDataBrowserElement.insertCell(0).appendChild(demoDataTreeDiv);
    
    
    //------------------------------------------------
    // create the yui tree view that will display the 
    // demo data directories
    //------------------------------------------------
    self.treeView = new YAHOO.widget.TreeView(demoDataTreeDiv.id);
    
    function loadNodeData(node, loadCompleteCallback) {
      // the response handler is a callback that is called when the response
      // to the generic request below is received. It will populate the
      // current node.
      var responseHandler = function(result, parentNode) {
        try {
          if (result && (result.length == 1) && result[0]) {
            if (result[0].directories) {
              var directories = result[0].directories;
              for (var i=0; i<directories.length; i++) {
                var tmpNode = new YAHOO.widget.TextNode(directories[i].name, node, false);
                if (!directories[i].hasSubDirs) {
                  tmpNode.isLeaf = true;
                }
              }
            }
          }
          
          loadCompleteCallback();
        } catch (e) {
          gApp.logException(e);
        }
      };
      
      // the function handleDemoDataRequest of the macro module on the server
      // will be called
      var functionName = "handleDemoDataRequest"; 
      
      // send the demo data directory to the server, so that it will in turn
      // send its contents as a response
      
      var arguments = [self.getDirectoryFromNode(node)];
      
      // send a generic request to the macro module on the server to ask for
      // the data of the current node
      var moduleContext = gApp.getModuleContext("DemoModulePanelDiv");
      moduleContext.sendGenericRequest(functionName, arguments, 
                                       function(result) { responseHandler(result, node); } );
    };
   
    // set the callback function for loading the tree data dynamically
    self.treeView.setDynamicLoad(loadNodeData);
  
    // get root node for tree and insert the top level node
    var root = self.treeView.getRoot();
    new YAHOO.widget.TextNode("DemoData", root, false); 
    
    // register click event handler
    self.treeView.subscribe("clickEvent", self.handleTreeViewClickEvent);
  
    // render tree with these toplevel nodes; all descendants of these nodes
    // will be generated as needed by the dynamic loader.
    self.treeView.draw();
  }
  
  
  //=============================================================================
  // handleTableRowSelected()
  //=============================================================================
  this.handleTableRowSelected = function (event, arg) {
    var name = event.target.cells[1].textContent;
    var path = event.target.cells[0].textContent;
    self.fileListTable.onEventSelectRow(event, arg);
    var moduleContext = gApp.getModuleContext("DemoModulePanelDiv");
    moduleContext.getModule().getField("filename").setValue("$(DemoDataPath)/" + path);
    moduleContext.getModule().getField("viewAll").trigger();
  }
  
  
  //=============================================================================
  // handleTreeViewClickEvent()
  //=============================================================================
  this.handleTreeViewClickEvent = function (event) {
    
    var updateFilesList = function(node) {
      self.fileListTable.deleteRows(0, self.fileListTable.getRecordSet().getLength());
      try {
        var rows = [];
        for (var i=0; i<node.files.length; i++) {
          rows.push({Name: node.files[i].name, Path: node.files[i].relativePath});
        }
        self.fileListTable.addRows(rows);
      } catch (e) {
        gApp.logException(e);
      }
    };
    
    if (!event.node.files) {
      self.loadDemoDataFiles(event.node, updateFilesList);
    } else {
      updateFilesList(event.node);
    }
  }
  

}
