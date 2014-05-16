// 10 okt 2011 sjoerd
// Viewer for screenshots of result images. Works together calls aps.net methods
// to get links to remote images to display
//
// 10-10-2011   Sjoerd  V1      -   just copied javascript from displayResultNotApproved to here to test import
// 10-10-2011   Sjoerd  V1.1    -   seperated code into sections, added renderResultViewerGUI function to make
//                                  inlcuding the resultviewer on a page just a matter creating one div and then
//                                  calling one function, instead of having to copy the entire GUI html code.




//======================== Parmeters =============================================================================
LOADING_IMAGE_URL = "/static/js/challengeResultViewer/ajax-loader.gif";


//======================== GUI (creating html elements) ==========================================================
// These functions are only used at page creation, to show buttons, inputs, text, etc.


//create the results viewer GUI inside the (div) element 'base' given as input.
//names in the GUI are identifiers and are hooked on by resultsViewer functions 
//restricted = true means only certain scans are loadable
function ResultViewerGUI() {
	var self = this;
	
	var default_options = {restricted: true,
                           image_url:'/static/site/VESSEL12/serve/',
                           files:[]
                           };
						   
	
	this.init = function(base,input_options){
		input_options = typeof(input_options) != 'undefined' ? input_options : {}; //default to empty list if no options given 
		self.base = base;
		log("init viewer in element '"+self.base+"'");		
		self.input_options = input_options;
			    
		var input_options = self.input_options;
		
		
		
						 
						  
		// Merge defaults and options passed when calling this function. Take default
		// if a key is not defined in input  
		var options = $.extend({},default_options,input_options);
		
		this.options = options;
		
		log("viewer options were'"+options+"'");
				
		var table = $("<table>");
		var tr = $("<tr>");


		var row1 = $("<div>");
		
		row1.append(this.createCheckboxElement("showOrg", true, "show original scan"));    
		row1.append(this.createCheckboxElement("showRes", true, "show current result: " + $("#resultDir").val()));    
		row1.append(this.createLabel("method1", "show additional results:"));    
		row1.append(this.createStringDropdownBoxAndBreak("method1",$.merge(["None"], this.getAllResultsExceptCurrent())));    
		row1.append(this.createStringDropdownBoxAndBreak("method2",$.merge(["None"], this.getAllResultsExceptCurrent())));
		row1.append(this.createCheckboxElement("showAll", false, "show all results"));    

		var row2 = $("<div>");    
		row2.append(this.createLabel("Item", "Item"));
		row2.append(this.createStringDropdownElement("Item",["DenseAbnormalities.png",
														"Fibrosis.png",
														"MucusFilledBronchus.png",
														"nodule_01.png",
														"nodule_02.png",
														"nodule_03.png",
														"nodule_04.png",
														"nodule_05.png",
														"nodule_06.png",
														"nodule_07.png",
														"nodule_08.png",
														"nodule_09.png",
														"nodule_10.png",
														"nodule_11.png",
														"nodule_12.png",
														"nodule_13.png",
														"nodule_14.png",
														"nodule_15.png",
														"VESSEL12_01_Slice_126.png",
														"VESSEL12_01_Slice_155.png",
														"VESSEL12_01_Slice_212.png",
														"VESSEL12_01_Slice_240.png",
														"VESSEL12_02_Slice_146.png",
														"VESSEL12_02_Slice_186.png",
														"VESSEL12_02_Slice_265.png",
														"VESSEL12_02_Slice_304.png",
														"VESSEL12_03_Slice_164.png",
														"VESSEL12_03_Slice_213.png",
														"VESSEL12_03_Slice_311.png",
														"VESSEL12_03_Slice_360.png",
														"VESSEL12_04_Slice_164.png",
														"VESSEL12_04_Slice_202.png",
														"VESSEL12_04_Slice_278.png",
														"VESSEL12_04_Slice_316.png",
														"VESSEL12_05_Slice_163.png",
														"VESSEL12_05_Slice_197.png",
														"VESSEL12_05_Slice_264.png",
														"VESSEL12_05_Slice_298.png",
														"VESSEL12_06_Slice_166.png",
														"VESSEL12_06_Slice_191.png",
														"VESSEL12_06_Slice_240.png",
														"VESSEL12_06_Slice_264.png",
														"VESSEL12_07_Slice_177.png",
														"VESSEL12_07_Slice_208.png",
														"VESSEL12_07_Slice_271.png",
														"VESSEL12_07_Slice_302.png",
														"VESSEL12_08_Slice_154.png",
														"VESSEL12_08_Slice_192.png",
														"VESSEL12_08_Slice_268.png",
														"VESSEL12_08_Slice_306.png",
														"VESSEL12_09_Slice_204.png",
														"VESSEL12_09_Slice_253.png",
														"VESSEL12_09_Slice_350.png",
														"VESSEL12_09_Slice_399.png",
														"VESSEL12_10_Slice_176.png",
														"VESSEL12_10_Slice_210.png",
														"VESSEL12_10_Slice_277.png",
														"VESSEL12_10_Slice_310.png",
														"VESSEL12_11_Slice_184.png",
														"VESSEL12_11_Slice_209.png",
														"VESSEL12_11_Slice_260.png",
														"VESSEL12_11_Slice_285.png",
														"VESSEL12_12_Slice_173.png",
														"VESSEL12_12_Slice_202.png",
														"VESSEL12_12_Slice_259.png",
														"VESSEL12_12_Slice_288.png",
														"VESSEL12_13_Slice_206.png",
														"VESSEL12_13_Slice_246.png",
														"VESSEL12_13_Slice_325.png",
														"VESSEL12_13_Slice_365.png",
														"VESSEL12_14_Slice_182.png",
														"VESSEL12_14_Slice_207.png",
														"VESSEL12_14_Slice_256.png",
														"VESSEL12_14_Slice_281.png",
														"VESSEL12_15_Slice_203.png",
														"VESSEL12_15_Slice_221.png",
														"VESSEL12_15_Slice_256.png",
														"VESSEL12_15_Slice_274.png",
														"VESSEL12_16_Slice_153.png",
														"VESSEL12_16_Slice_204.png",
														"VESSEL12_16_Slice_307.png",
														"VESSEL12_16_Slice_358.png",
														"VESSEL12_17_Slice_249.png",
														"VESSEL12_17_Slice_265.png",
														"VESSEL12_17_Slice_296.png",
														"VESSEL12_17_Slice_311.png",
														"VESSEL12_18_Slice_139.png",
														"VESSEL12_18_Slice_172.png",
														"VESSEL12_18_Slice_238.png",
														"VESSEL12_18_Slice_271.png",
														"VESSEL12_19_Slice_177.png",
														"VESSEL12_19_Slice_205.png",
														"VESSEL12_19_Slice_262.png",
														"VESSEL12_19_Slice_290.png",
														"VESSEL12_20_Slice_154.png",
														"VESSEL12_20_Slice_176.png",
														"VESSEL12_20_Slice_220.png",
														"VESSEL12_20_Slice_242.png",
														"Vessels.png"
													])) //create box containing only allowed elements    

		var row3 = $("<div>");

		row3.append(this.createLabel("Width", "Image width in pixels"));
		row3.append(this.createIntSelectBox("Width", 200));
		row3.append($("<br/>"));
		row3.append(this.createLabel("ShowHeaders", "Show info headers for each image"));
		row3.append(this.createCheckBox("ShowHeaders", true));
		row3.append($("<br/>"));


		$(self.base).append(this.createSingleRowTable([row1, row2, row3]));
		$(self.base).append(this.createSubmitButton("loadButton", "Load"));
		
		this.init_hooks();

					
	}//end init
	
	//return a table with a single row, each element in elements in its own column
    this.createSingleRowTable = function(elements){
        var table = $("<table>");
        var tr = $("<tr>");
        tr.appendTo(table);
        $.each(elements, function (index, element) {
            var td = $("<td>");
            if (index == elements.length - 1) {
                td.attr("class", "resultviewerControlsLastColumn");
            } else {
                td.attr("class", "resultviewerControlsColumn");
            }
            td.append(element);
            td.appendTo(tr);
    
        });
        return table;
    }
    
        //create a checkbox inside a div, with label. 
    //example:
    //<div class="editor-label"> <input id="showRef" name="showRef" type="checkbox" checked="checked"/> <label for="reference">reference</label> </div>
     this.createCheckboxElement = function(id, checked, labelText) {
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-label");
    
        var checkBox = this.createCheckBox(id, checked);
    
        var label = this.createLabel(id, labelText);
    
        containerDiv.append(checkBox);
        containerDiv.append(label);
        return containerDiv;
    }
    
    //create this:
    //<input class="" id="id" name="id" type="checkbox" checked=checked /> 
    this.createCheckBox = function(id, checked) {
        var checkBox = $('<input type="checkbox"/>');
        checkBox.attr('id', id);
        checkBox.attr('name', id);
    
        if (checked) {
            checkBox.attr('checked', "checked");
        }
        return checkBox;
    }
    
    
    //create this:
    //<label for="id">labelText</label><br/>
    this.createLabel = function(forId, labelText) {
        var label = $("<label>");
        label.attr("for", forId);
        label.html(labelText);
        label.append($("<br/>"));
        return label;
    }
    
    //create this:
    //<input class="text-box single-line" id=id name=id type="text" value=value" />
    this.createIntSelectBox = function(id, startVal) {
        var textBox = $('<input type="text"/>');
        textBox.attr('class', "intSelectTextBox");
        textBox.attr('id', id);
        textBox.attr('name', id);
        textBox.attr('value', startVal);
        return textBox;
    }
    
    //create this:
    //<select>  <option>options[0]</option>... </select>  
    this.createIntDropdownBox = function(id, options) {
        var selectBox = $('<select>');
        selectBox.attr('class', "intSelectTextBox");
        selectBox.attr('id', id);
        selectBox.attr('name', id);
        //selectBox.attr('value', startVal);    
        $.each(options, function(i,value) {
            option = $("<option />")
            option.val(value)
            option.text(value)
            selectBox.append(option);
        });    
    
        return selectBox;
    }
    
    //create this:
    //<select>  <option>options[0]</option>... </select>  
    this.createStringDropdownBox = function(id, options) {
        var selectBox = $('<select>');
        selectBox.attr('class', "stringSelectTextBox");
        selectBox.attr('id', id);
        selectBox.attr('name', id);
        //selectBox.attr('value', startVal);    
        $.each(options, function(i,value) {
            option = $("<option />")
            option.val(value)
            option.text(cleanResultName(value))
            selectBox.append(option);
        });    
    
        return selectBox;
    }
    
    //create this:
    //<input type="submit" value=buttonText id=id />
    this.createSubmitButton = function(id, buttonText) {
        var button = $('<input type="submit"/>');
        button.attr("id", id);
        button.attr("value", buttonText);
        return button;
    }
    
    //create something like this:
    //<div class="editor-field">
    //      <input type="submit" value="prev" id="prevScanButton" />
    //      <input class="text-box single-line" id="Scan" name="Scan" type="text" value="1" style="width:3em;" />
    //      <input type="submit" value="next" id="nextScanButton" />
    //</div>
    this.createIntSelectElement = function(id, startVal) {
        var prevButton = this.createSubmitButton("prev" + id + "Button", "prev");
        var textBox = createIntSelectBox(id, startVal);    
        var nextButton = this.createSubmitButton("next" + id + "Button", "next");
    
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");
    
        containerDiv.append(prevButton);
        containerDiv.append(textBox);
        containerDiv.append(nextButton);
    
        return containerDiv;
    
    }
    
    //create 'select' element dropdownbox with buttons
    this.createIntDropdownElement = function(id, options) {
        var prevButton = this.createSubmitButton("prev" + id + "Button", "prev");    
        var textBox = createIntDropdownBox(id, options);
        var nextButton = this.createSubmitButton("next" + id + "Button", "next");
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");
    
        containerDiv.append(prevButton);
        containerDiv.append(textBox);
        containerDiv.append(nextButton);
    
        return containerDiv;
    
    }
	
    //create 'select' element by itself
    this.createStringDropdownBoxAndBreak = function(id, options) {    
        var textBox = this.createStringDropdownBox(id, options);    
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");    
        containerDiv.append(textBox);
        containerDiv.append($("<br/>"));
    
        return containerDiv;    
    }
    
    //create 'select' element dropdownbox
    this.createStringDropdownElement = function(id, options) {
        var prevButton = this.createSubmitButton("prev" + id + "Button", "prev");    
        var textBox = this.createStringDropdownBox(id, options);
        var nextButton = this.createSubmitButton("next" + id + "Button", "next");
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");
    
        containerDiv.append(prevButton);
        containerDiv.append(textBox);
        containerDiv.append(nextButton);
    
        return containerDiv;
    
    }
    
    //return all results, except the one for which this page is made
    this.getAllResultsExceptCurrent = function(){
        all =  this.getAllResults();
        var clean = removeFromArray(all,$("#resultDir").val());
        return clean
    }
    
    //Return all results which can be compared 
    this.getAllResults = function(){
    //TODO: get all results dynamically
        allResults =   ["20120227124320_104_DIAG_HUVesselSeg",
                        "20120322112800_189_MEDKIS_MedKIS_SDTF",
                        "20120322173351_193_Labhuman_VESSEL12_Results_Labhuman_SDTF",
                        "20120322173822_104_DIAG_DIAGvesselSegDistanceTrans",
                        "20120322174031_104_DIAG_VesselnessVesselSegMultiScale1To4_5mm7steps",
                        "20120327190226_124_TSSeg_TSSeg_SDTF",
                        "20120328103053_163_LKEBChina_VESSEL12_Frangi",
                        "20120328103158_163_LKEBChina_VESSEL12_ModifiedKrissian",
                        "20120328103231_163_LKEBChina_VESSEL12_ModifiedKrissian-BG",
                        "20120328103241_163_LKEBChina_VESSEL12_StrainEnergy",
                        "20120330201457_261_FME_LungVessels_fmehb_submission",
                        "20120331164606_207_ntnu_RESULTS_SDTF",
                        "20120331210951_157_CREALUNG_VESSEL12_RESULTS_SDTF",
                        "20120401181329_121_Bahcesehir_University_Vessel12Segmentations_ilkayoksuz",
                        "20120402010231_77_ASBMI_WenzheXue_Seg_Apr1",
                        "20120402083108_181_SU_UT_SU_UT_Results",
                        "20120404164944_146_simira_SimiraResults_PleaseEvaluateThisOne_SDTF",
                        "20120412152635_261_FME_LungVessels_fmehb_vesselness_only_submission",
                        "20120416175045_249_ARTEMIS-TSP_VESSE12_Results_ARTEMIS-TSP_Results",
                        "20120416220123_256_BWH-ACIL_VesselProbability-BWHACIL"
        ];
    
    
        return allResults;
        }
		//======================== functions ===================================================================================
	// Anything called while interacting with the GUI

	this.loadAllScreenshots = function(){
		//var params = getDisplayScreenshotParams();
		var params = {resultDirs:["dir1","dir2"]};
		var width = $("#Width").val();
			

		$("#resultMessage").html(""); //clear previous images

		// params yields an array results folders. For each result params with only
		// one result, and ask for a screenshot link to each one.

		//first create a space for each image. This has to be done before asynchronously loading to make sure the order of scans is correct.
		//For each image a container div is created with a unique id. To this container the image itself is added later.
		
		$.each(params["resultDirs"], function (index, value) {
			var paramsCurrent = params;
			paramsCurrent["resultDirs"] = value;

			// create a block with a header which image is being shown and the image below that
			var header = $("<div>"); //create a header showing which type of image this is
			header.html(paramsToString(paramsCurrent));
			header.addClass("resultImageHeader");

			var image = $("<div>"); //create container for image                
			image.addClass("resultImage");
			// Put an animated GIF image insight of content
			image.html("<img src=\""+LOADING_IMAGE_URL+"\">");  

			var container = $("<div>"); //create container to hold header + image
			container.append(header);
			container.append(image);
			container.addClass("resultImageContainer");
			var containerId = paramsToId(paramsCurrent);  //get unique html id based on these params
			container.attr("id", containerId);
			container.width(width + "px");
			//set height to make sure the screen does shift while images are loading
			container.height(width + "px");

			$("#resultMessage").append(container);

		});

		//show or hide headers according to what is set in checkbox "ShowHeaders"
		setHeaders();
		//params have been changed from array to one item of this array by the previous loop. Why? To fix just get params again.
		var params = getDisplayScreenshotParams();
		//After creating containers, try to fill each.
		
		$.each(params["resultDirs"], function (index, value) {
			var paramsCurrent = params;
			paramsCurrent["resultDirs"] = value;
			//console.info("getting link..");
			$.post("../serve/public_html/test_1.PNG/",
					function (data) {// create a block with a header which image is being shown and the image below that                    
						paramsCurrent["resultDirs"] = value; //this needs to be set again for some reason. Otherwise first paramsCurrent will be used always
						var resultImageId = paramsToId(paramsCurrent)  //get unique html id based on these params
						var container = $("#" + resultImageId + " .resultImage");
						container.empty(); //remove loading animation

						if (isUrl(data)) {  //check whether string returned is actually an url. If not it is an error message
							container.append(htmlImage(data, width));

						} else {
							container.append(htmlImageError(data, width));
						}
					});

			var resultImageId = paramsToId(paramsCurrent)  //get unique html id based on these params
			var container = $("#" + resultImageId + " .resultImage");
			
			container.empty(); //remove loading animation
			
	   
		});
		


	}
	
	this.init_hooks = function(){		
		
		$(function () {
			$("#loadButton").click(function () {
				self.loadAllScreenshots();
			});

		});

		$(function () {
			$("#prevItemButton").click(function () {
				var prevAllowed = givePrevDropdownValueName("#Item")
				$("#Item").val(prevAllowed);
				self.loadAllScreenshots();        
			});

		});

		$(function () {
			$("#nextItemButton").click(function () {        
				var nextAllowed = giveNextDropdownValueName("#Item")
				$("#Item").val(nextAllowed);
				self.loadAllScreenshots();
			});

		});



		$(function () {
			$("#Width").keypress(function (e) {
				//if enter is pressed
				code = (e.keyCode ? e.keyCode : e.which);
				if (code == 13) {
					var width = $("#Width").val();
					setAllImageWidths(width);
				}
			});

		});

		$(function () {
			$("#ShowHeaders").change(function () {
				setHeaders();
			});

		});


		$(function () {
			$("#showAll").click(function () {                
				self.loadAllScreenshots();
				if ($("#showAll").attr("checked")) {
					
					$("#showOrg").attr("disabled","true");
					$("#showRes").attr("disabled","true");
					$("#method1").attr("disabled","true");
					$("#method2").attr("disabled","true");
				}else{
					$("#showOrg").removeAttr("disabled");
					$("#showRes").removeAttr("disabled","false");
					$("#method1").removeAttr("disabled","false");
					$("#method2").removeAttr("disabled","false");
				}

			});

		});

		$(function () {
			$("#showOrg").click(function () {                
				self.loadAllScreenshots();
			});

		});

		$(function () {
			$("#showRes").click(function () {                
				self.loadAllScreenshots();
			});

		});

		$(function () {
			$("#method1").change(function () {                
				self.loadAllScreenshots();
			});

		});

		$(function () {
			$("#method2").change(function () {                
				self.loadAllScreenshots();
			});

		});

		$(function () {
			$("#Item").change(function () {                
				self.loadAllScreenshots();
			});

		});


		//======================== end hooking functions to GUI element ========================================================

	}

	
	
    
}//end ResultViewerGUI



//======================== end GUI (creating html elements) ========================================================



//======================== hooking functions to GUI element ========================================================

$(document).ready(function () {
    //nothing
});




//======================== end hooking functions to GUI element ========================================================


//======================== functions ===================================================================================
// Anything called while interacting with the GUI

function loadAllScreenshots() {

    
    //var params = getDisplayScreenshotParams();
    var params = {resultDirs:["dir1","dir2"]};
    var width = $("#Width").val();
        

    $("#resultMessage").html(""); //clear previous images

    // params yields an array results folders. For each result params with only
    // one result, and ask for a screenshot link to each one.

    //first create a space for each image. This has to be done before asynchronously loading to make sure the order of scans is correct.
    //For each image a container div is created with a unique id. To this container the image itself is added later.
    
    $.each(params["resultDirs"], function (index, value) {
        var paramsCurrent = params;
        paramsCurrent["resultDirs"] = value;

        // create a block with a header which image is being shown and the image below that
        var header = $("<div>"); //create a header showing which type of image this is
        header.html(paramsToString(paramsCurrent));
        header.addClass("resultImageHeader");

        var image = $("<div>"); //create container for image                
        image.addClass("resultImage");
        // Put an animated GIF image insight of content
        image.html("<img src=\""+LOADING_IMAGE_URL+"\">");  

        var container = $("<div>"); //create container to hold header + image
        container.append(header);
        container.append(image);
        container.addClass("resultImageContainer");
        var containerId = paramsToId(paramsCurrent);  //get unique html id based on these params
        container.attr("id", containerId);
        container.width(width + "px");
        //set height to make sure the screen does shift while images are loading
        container.height(width + "px");

        $("#resultMessage").append(container);

    });

    //show or hide headers according to what is set in checkbox "ShowHeaders"
    setHeaders();
    //params have been changed from array to one item of this array by the previous loop. Why? To fix just get params again.
    var params = getDisplayScreenshotParams();
    //After creating containers, try to fill each.
    
    $.each(params["resultDirs"], function (index, value) {
        var paramsCurrent = params;
        paramsCurrent["resultDirs"] = value;
        //console.info("getting link..");
        $.post("../serve/public_html/test_1.PNG/",
                function (data) {// create a block with a header which image is being shown and the image below that                    
                    paramsCurrent["resultDirs"] = value; //this needs to be set again for some reason. Otherwise first paramsCurrent will be used always
                    var resultImageId = paramsToId(paramsCurrent)  //get unique html id based on these params
                    var container = $("#" + resultImageId + " .resultImage");
                    container.empty(); //remove loading animation

                    if (isUrl(data)) {  //check whether string returned is actually an url. If not it is an error message
                        container.append(htmlImage(data, width));

                    } else {
                        container.append(htmlImageError(data, width));
                    }
                });

        var resultImageId = paramsToId(paramsCurrent)  //get unique html id based on these params
        var container = $("#" + resultImageId + " .resultImage");
        
        container.empty(); //remove loading animation
        
   
    });


}


function loadAllScreenshots_org() {

    var params = getDisplayScreenshotParams();
    var width = $("#Width").val();
        

    $("#resultMessage").html(""); //clear previous images

    // params yields an array results folders. For each result params with only
    // one result, and ask for a screenshot link to each one.

    //first create a space for each image. This has to be done before asyncronously loading to make sure the order of scans is correct.
    //For each image a container div is created with a unique id. To this container the image itself is added later.
    
    $.each(params["resultDirs"], function (index, value) {
        var paramsCurrent = params;
        paramsCurrent["resultDirs"] = value;

        // create a block with a header which image is being shown and the image below that
        var header = $("<div>"); //create a header showing which type of image this is
        header.html(paramsToString(paramsCurrent));
        header.addClass("resultImageHeader");

        var image = $("<div>"); //create container for image                
        image.addClass("resultImage");
        // Put an animated GIF image insight of content
        image.html("<img src=\""+LOADING_IMAGE_URL+"\">");  

        var container = $("<div>"); //create container to hold header + image
        container.append(header);
        container.append(image);
        container.addClass("resultImageContainer");
        var containerId = paramsToId(paramsCurrent);  //get unique html id based on these params
        container.attr("id", containerId);
        container.width(width + "px");
        //set height to make sure the screen does shift while images are loading
        container.height(width + "px");

        $("#resultMessage").append(container);

    });

    //show or hide headers according to what is set in checkbox "ShowHeaders"
    setHeaders();
    //params have been changed from array to one item of this array by the previous loop. Why? To fix just get params again.
    var params = getDisplayScreenshotParams();
    //After creating containers, try to fill each.
    
    $.each(params["resultDirs"], function (index, value) {
        var paramsCurrent = params;
        paramsCurrent["resultDirs"] = value;
        //console.info("getting link..");
        $.post("/Results/getVESSEL12ScreenshotLink", {resultId:paramsCurrent["resultDirs"],type:paramsCurrent["authenticationType"],fileName:paramsCurrent["item"]},
                function (data) {// create a block with a header which image is being shown and the image below that                    
                    paramsCurrent["resultDirs"] = value; //this needs to be set again for some reason. Otherwise first paramsCurrent will be used always
                    var resultImageId = paramsToId(paramsCurrent)  //get unique html id based on these params
                    var container = $("#" + resultImageId + " .resultImage");
                    container.empty(); //remove loading animation

                    if (isUrl(data)) {  //check whether string returned is actually an url. If not it is an error message
                        container.append(htmlImage(data, width));

                    } else {
                        container.append(htmlImageError(data, width));
                    }
                });

        var resultImageId = paramsToId(paramsCurrent)  //get unique html id based on these params
        var container = $("#" + resultImageId + " .resultImage");
        
        container.empty(); //remove loading animation
        
   
    });


}



//used to scale images after being loaded in results viewer
function setAllImageWidths(widthIn) {
    //set width of container itself
    $(".resultImageContainer").width(widthIn + "px");
    //set height as well, this is set when loading to make sure the screen does not shift while images load into divs.
    //when resizing here, set this too because otherwise the images can go through the footer
    $(".resultImageContainer").height(widthIn + "px");
    //set width of image inside container
    $(".resultImageContainer img").width(widthIn + "px");
    //set width of error div if any.    
    $(".resultImageContainer div").width(widthIn + "px");

}

//Print info headers above each image or not, according to checkbox named "ShowHeaders"
function setHeaders() {

    var bool = $("#ShowHeaders").is(":checked");
    if (bool == true) {
        $(".resultImageHeader").show();
    } else if (bool == false) {
        $(".resultImageHeader").hide();
    }
    //todo throw some error on wrong param?
}


//used to differentiate between error and succes response from getLola11ScreenshotLink
function isUrl(string) {
    if (string.substring(0, 4) == "http") {
        return true;
    }else if(string.substring(0, 1) == "/"){ //also allow relative urls
        return true;
    }
     else {
        return false;
    }

}

function getDisplayScreenshotParams() {
    // returns a full description of all scans that should be loaded and how
    //{ resultId: resultIdVal,
    //  resultDir: resultDirVal,
    //  item: itemVal, 
    //  authenticationType: authenticationTypeVal,
    //  type: typeVals, 
    //  resultDirs: resultDirs
    //}
    
    var resultIdVal = $("#resultId").val(); //this is a hidden var at the top of the page, filled by asp.net.            
    var resultDirVal = $("#resultDir").val(); //this is a hidden var at the top of the page, filled by asp.net.            
    var authenticationTypeVal = $("#authenticationType").val(); //this is a hidden var at the top of the page, filled by asp.net.                
    var itemVal = $("#Item").val();

    var resultDirs = []; //for each result to compare with, add the result dir to this list
    
    if ($("#showOrg").attr("checked")) {
        resultDirs.push("originalScans"); //push this result last to make it first in row
    }
    
    if ($("#showRes").attr("checked")) {
        resultDirs.push($("#resultDir").val()); //push this result last to make it first in row
    }

    if ($("#method1").val() != "None"){
        resultDirs.push($("#method1").val());
    }
    if ($("#method2").val() != "None"){
        resultDirs.push($("#method2").val());
    }
    
    

    

    if ($("#showAll").attr("checked")) {
        
        resultDirs = $.merge(resultDirs, getAllResults());
        resultDirs = removeDuplicates(resultDirs);
        
    }



    var typeVals = [];  //for each checkbox, if checked add this result type to the list of types to be shown

    if ($("#showDif").attr("checked")) {
        typeVals.push("dif");
    }
    if ($("#showOrg").attr("checked")) {
        typeVals.push("orgScan");
    }
    if ($("#showRes").attr("checked")) {
        typeVals.push("res");
    }
    if ($("#showRef").attr("checked")) {
        typeVals.push("ref");
    }

    // poor man's validation
    // add later?
    return { resultId: resultIdVal, resultDir: resultDirVal, item: itemVal, authenticationType: authenticationTypeVal, type: typeVals, resultDirs: resultDirs};
}

//return array
function removeDuplicates(array){

    var seen = {}
    var cleaned = []
    $.each(array,function(index,value){
        
        if (seen[value]){
            //do nothing
            }
        else{
            seen[value] = true;
            cleaned.push(value);
            }
    });
    return cleaned;
}

//remove each occurrence of item from array
function removeFromArray(array,item){
    
    var cleaned = []
    $.each(array,function(index,value){
        
        if (value == item){
            //do nothing
            }
        else{
            cleaned.push(value);
            }
    });
    return cleaned;
}


function test(array){
    $.each(array,function(index,value){
        console.log(value + "&&");
    });
    
}



//for diplaying parameters of a scan screenshot on screen.
function paramsToString(params) {
    
    var output = params["resultDirs"];
    output = cleanResultName(output) //for vessel12 this makes the names more pallatable

    return output;
}

//from params, create a unique Id to be used in an html element
function paramsToId(params) {

    //For vessel12, the resultDir item is unique
    return params["resultDirs"];
}

function objectToString(obj) {
    var output = '';
    for (property in obj) {
        output += property + ': ' + obj[property] + '; ';
    }
    return output;
}


//go from "20120404182013_109_CIMA_BWH-ACIL_VesselProbability-BWHACIL" to "CIMA_BWH-ACIL_VesselProbability-BWHACIL" to make a more informative string
function cleanResultName(resultNameString){
    var clean = resultNameString;
    if(resultNameString[14] == "_"){
        clean = clean.slice(15)
    }
    ns = clean.indexOf("_"); //position of next underscore 
    if(ns <= 4){
        clean = clean.slice(ns+1);
    }
     return clean

}


//create HTML element showing and linking to given url
function htmlImage(url, width) {



    //make something like this: "<a href='" + url + "'><img src ='" + url + "' width='"+width+"' /></a>";
    var imageLink = $('<a>');
    imageLink.attr("href", url);

    var image = $('<img>');
    image.attr("src", url);
    image.width(width);

    imageLink.append(image)

    return imageLink;

}

//create square HTML element showing error text with the same width as image. For displaying an image like element with error.
function htmlImageError(msg, width) {

    var errorElement = $("<div>");
    errorElement.html(msg);
    errorElement.addClass("generalChallengeError");
    //errorElement.width(width);
    //errorElement.height(width);

    //.attr('class','generalChallengeError')  "<div class = 'generalChallengeError' style =kees></div>";  // 'width " + width + " height " + width + "' >" + msg + "</div>";


    return errorElement;

}


function getAllAllowedScans(){    
    var allowedScans = $("#allowedScans").val(); //this is a hidden var at the top of the page, filled by asp.net.
    allowedScanArray = allowedScans.split(",");
    for(var i=0, len=allowedScanArray.length; i<len; i++){
        allowedScanArray[i] = parseInt(allowedScanArray[i], 10);
    }
    
    return allowedScanArray.sort(isGreaterThan)

}

//for sorting numbers using sort.. why is this not built in?
function isGreaterThan(a,b){

    return a-b //return positive if a is greater than b.
}



//returns true if this element is found inside current page.
function htmlTagExists(htmlTag){
    return $(htmlTag).length >= 1;
    
}

//checks the given dropdown item id for the name of the next option
function giveNextDropdownValueName(dropDownId){
    next = $(dropDownId + " option:selected").next().val()
    if(next === undefined){
        next = $(dropDownId).val() //if next item does not exist, stay at current item
    };

    return next

}

function givePrevDropdownValueName(dropDownId){
    prev = $(dropDownId + " option:selected").prev().val()
    if(prev === undefined){
        prev = $(dropDownId).val() //if next item does not exist, stay at current item
    };

    return prev

}

function log(msg){
    console.log("* "+msg);
}


// ======================== make ajax calls work with csrf protection ==================
function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

var csrftoken = $.cookie('csrftoken');

$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

//======================== end functions ===================================================================================

//======================== end functions ===================================================================================