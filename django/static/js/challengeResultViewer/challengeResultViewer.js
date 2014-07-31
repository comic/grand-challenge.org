// 10 okt 2011 sjoerd
// Viewer for screenshots of result images. Works together calls aps.net methods
// to get links to remote images to display
//
// 10-10-2011   Sjoerd  V1      -   just copied javascript from displayResultNotApproved to here to test import
// 10-10-2011   Sjoerd  V1.1    -   seperated code into sections, added renderResultViewerGUI function to make
//                                  inlcuding the resultviewer on a page just a matter creating one div and then
//                                  calling one function, instead of having to copy the entire GUI html code.


//======================== Parameters =============================================================================
LOADING_IMAGE_URL = "/static/js/challengeResultViewer/ajax-loader.gif";


//======================== GUI (creating html elements) ==========================================================
// These functions are only used at page creation, to show buttons, inputs, text, etc.

//create the results viewer GUI inside the (div) element 'base' given as input.
//names in the GUI are identifiers and are hooked on by resultsViewer functions 
//restricted = true means only certain scans are loadable
function ResultViewerGUI() {
    var self = this;
    
    var default_options = {restricted: true,
                           //prepend this to filename to serve images from project data folder
                           static_url:'/site/VESSEL12/serve/',
                           controls:{tickboxes:[],
                                     selectionboxes:[["default","default",["option1","option2"]]],
                                     imagePathsFunction:undefined
                                 },
                           };
                           
    this.init = function(base,input_options){
        input_options = typeof(input_options) != 'undefined' ? input_options : {}; //default to empty list if no options given         
        self.base = base;
        
        log("init viewer in element '"+self.base+"'");        
        self.input_options = input_options;
        var input_options = self.input_options;
        
        // Merge defaults and options passed when calling this function. Take default
        // if a key is not defined in input  
        self.options = $.extend({},default_options,input_options);
        
        //assigning a function here
        if(self.options["imagePathsFunction"] == undefined){
            log("No custom imagePathsFunction defined. using standard");
            self.setImagePathsFunction(getImagePaths);
        }else{
            self.setImagePathsFunction(self.options["imagePathsFunction"]);
            
        };
        
        log("viewer options were'"+JSON.stringify(self.options)+"'");
                
        var table = $("<table>");
        var tr = $("<tr>");

        var row1 = $("<div>");
        // initialize all gui controls that user can use to browse through the
        // images
        self.options.controls.tickboxes.forEach(function (value, index) {
            log("creating tickbox based on" + JSON.stringify(value));            
            row1.append(self.createCheckboxElement(value[0],value[1],value[2]));
        });
        

        var row2 = $("<div>");
        self.options.controls.selectionboxes.forEach(function (value, index) {
            log("creating selectionbox based on" + JSON.stringify(value));
            row2.append(self.createLabel(value[0], value[1]));
            row2.append(self.createStringDropdownElement(value[1],self.options["fileNames"])); //create box containing only allowed elements                        
        });

        var row3 = $("<div>");

        row3.append(this.createLabel("Width", "Image width in pixels"));
        row3.append(this.createIntSelectBox("Width", 200));
        row3.append($("<br/>"));
        row3.append(this.createLabel("ShowHeaders", "Show info headers for each image"));
        row3.append(this.createCheckBox("ShowHeaders", true));
        row3.append($("<br/>"));


        $(self.base).append(this.createSingleRowTable("controls",[row1, row2, row3]));
        $(self.base).append(this.createSubmitButton("loadButton", "Load"));
        
        this.init_hooks();
    };//end init
    
    this.setImagePathsFunction = function(imagePathsFunction){
        //The imagePathsFunction takes a single object (options) representing the state of all tickboxes
        // and dropdown menus, and returns an array of image paths to display 
        if(imagePathsFunction.prototype.toString() != "[object Object]"){
          log("this.setImagePathsFunction: single inputargument to this function should be a function, found "+imagePathsFunction.prototype.toString()+" instead.");
                 
        }else{
            self.getImagePaths = imagePathsFunction;
        };
        
          
    };
    
    //return a table with a single row, each element in elements in its own column
    this.createSingleRowTable = function(id, elements){
        var table = $("<table id = '"+ id +"'>");
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
    };
    
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
    };
    
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
    };
    
    
    //create this:
    //<label for="id">labelText</label><br/>
    this.createLabel = function(forId, labelText) {
        var label = $("<label>");
        label.attr("for", forId);
        label.html(labelText);
        label.append($("<br/>"));
        return label;
    };
    
    //create this:
    //<input class="text-box single-line" id=id name=id type="text" value=value" />
    this.createIntSelectBox = function(id, startVal) {
        var textBox = $('<input type="text"/>');
        textBox.attr('class', "intSelectTextBox");
        textBox.attr('id', id);
        textBox.attr('name', id);
        textBox.attr('value', startVal);
        return textBox;
    };
    
    //create this:
    //<select>  <option>options[0]</option>... </select>  
    this.createIntDropdownBox = function(id, options) {
        var selectBox = $('<select>');
        selectBox.attr('class', "intSelectTextBox");
        selectBox.attr('id', id);
        selectBox.attr('name', id);
        //selectBox.attr('value', startVal);    
        $.each(options, function(i,value) {
            option = $("<option />");
            option.val(value);
            option.text(value);
            selectBox.append(option);
        });    
    
        return selectBox;
    };
    
    //create this:
    //<select>  <option>options[0]</option>... </select>  
    this.createStringDropdownBox = function(id, options) {
        var selectBox = $('<select>');
        selectBox.attr('class', "stringSelectTextBox");
        selectBox.attr('id', id);
        selectBox.attr('name', id);
        //selectBox.attr('value', startVal);    
        $.each(options, function(i,value) {
            option = $("<option />");
            option.val(value);
            option.text(cleanResultName(value));
            selectBox.append(option);
        });    
    
        return selectBox;
    };
    
    //create this:
    //<input type="submit" value=buttonText id=id />
    this.createSubmitButton = function(id, buttonText) {
        var button = $('<input type="submit"/>');
        button.attr("id", id);
        button.attr("value", buttonText);
        return button;
    };
    
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
    
    };
    
    //create 'select' element dropdownbox with buttons
    this.createIntDropdownElement = function(id, options) {
        var prevButton = this.createSubmitButton("prev" + id + "Button", "prev");    
        var textBox = createIntDropdownBox(id, options);
        var nextButton = this.createSubmitButton("next" + id + "Button", "next");
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");
        containerDiv.attr("id", id);
    
        containerDiv.append(prevButton);
        containerDiv.append(textBox);
        containerDiv.append(nextButton);
    
        return containerDiv;
    
    };
    
    //create 'select' element by itself
    this.createStringDropdownBoxAndBreak = function(id, options) {    
        var textBox = this.createStringDropdownBox(id, options);    
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");    
        containerDiv.append(textBox);
        containerDiv.append($("<br/>"));
    
        return containerDiv;    
    };
    
    //create 'select' element dropdownbox
    this.createStringDropdownElement = function(id, options) {
        var prevButton = this.createSubmitButton("prev" + id + "Button", "prev");    
        var textBox = this.createStringDropdownBox(id, options);
        var nextButton = this.createSubmitButton("next" + id + "Button", "next");
        var containerDiv = $("<div>");
        containerDiv.attr("class", "editor-field");
        containerDiv.attr("id", id);
    
        containerDiv.append(prevButton);
        containerDiv.append(textBox);
        containerDiv.append(nextButton);
    
        return containerDiv;
    
    };
    
    //return all results, except the one for which this page is made
    this.getAllResultsExceptCurrent = function(){
        all =  this.getAllResults();
        var clean = removeFromArray(all,$("#resultDir").val());
        return clean
    };
    
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
    };
    
    
    this.createImagePlaceholder = function(id){
        // create a block with a header which image is being shown and the image below that
        log("creating space for '"+id+"'");
        
        var width = $("#Width").val();        
        var header = $("<div>"); //create a header showing which type of image this is
        header.html("header TODO");
        header.addClass("resultImageHeader");
        var image = $("<div>"); //create container for image                
        image.addClass("resultImage");
        // Put an animated GIF image insight of content
        image.html("<img src=\""+LOADING_IMAGE_URL+"\">");
        
        var container = $("<div>"); //create container to hold header + image
        container.append(header);
        container.append(image);
        container.addClass("resultImageContainer");    
        container.attr("id",id);
        container.width(width + "px");
        //set height to make sure the screen does shift while images are loading
        container.height(width + "px");
        return container;
    };
    
        
    this.fillImagePlaceholder = function(id,path){
        log("filling '"+id+"' with '" + path + "'");
        var width = $("#Width").val();
        var container = $("#"+id);        
        log("loading image '"+path+"' in div'"+id+"'");
        container.empty(); //remove loading animation
        container.append(htmlImage(path, width));        
        
};
    
        //======================== functions ===================================================================================
    // Anything called while interacting with the GUI

    this.loadAllScreenshots = function(){
        //var params = getDisplayScreenshotParams();
        //var params = {resultDirs:["public_html"],fileNames:["test_1.PNG","test_2.PNG"]};
        
        var params = this.options;
        log("loading all images, params are" + JSON.stringify(this.options));
        
        var imagePaths = self.getImagePaths(this.options);
        
        var width = $("#Width").val();
        var static_url = this.options["static_url"];
        
        $("#resultMessage").html(""); //clear previous images
        
        $.each(imagePaths, function (indexf, valuef){
            elementId = self.getUniqueId(valuef);
            var container = self.createImagePlaceholder(elementId);
            $("#resultMessage").append(container);
        });
        
        
        $.each(imagePaths, function (indexf, valuef){
            elementId = self.getUniqueId(valuef);
            self.fillImagePlaceholder(elementId,valuef);
            
        });
 
    };
    
    
    this.getUniqueId = function(filename,directory){
        //from params, create a unique Id to be used in an html element
        if(directory == null){
            var raw = self.base+"_"+filename;
        }else{
            var raw = self.base+"_"+directory+"_"+filename;            
        }
        return URLify(raw);
        
    };

    
    
    this.init_hooks = function(){
        
        //When any button is checked, load all screenshots
        this.options.controls.tickboxes.forEach(function (value, index) {            
            
            var selector = "input#"+value[0];
            log("hooking tickbox '" + selector + "'");
            $(function () {
                $(selector).click(function () {
                    self.loadAllScreenshots();});
            });
        });
        
        
        this.options.controls.selectionboxes.forEach(function (value, index) {
            var divselector = "div#"+value[0];
            log("hooking selectionbox in'" + divselector + "'");
            
            self.hookDropdownElement(divselector);
            //row2.append(self.createLabel(value[0], value[1]));
            //row2.append(self.createStringDropdownElement(value[1],self.options["fileNames"])); //create box containing only allowed elements                        
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
                $("#loadButton").click(function () {
                    self.loadAllScreenshots();});
            });


        //======================== end hooking functions to GUI element ========================================================

    };
    this.hookDropdownElement = function(divSelector){
        log("creating function hooks for dropdown \'" +divSelector+"\'");
        dropdownSelector = divSelector + " select";
        nextSelector = divSelector + " input#nextImageButton";
        prevSelector = divSelector + " input#prevImageButton";
        
        $(function () {
            $(dropdownSelector).click(function () {
                self.loadAllScreenshots();
            });
            
            $(nextSelector).click(function () {
                var nextAllowed = giveNextDropdownValueName(dropdownSelector);
                $(dropdownSelector).val(nextAllowed);
                self.loadAllScreenshots();
            });
            
            $(prevSelector).click(function () {
                var prevAllowed = givePrevDropdownValueName(dropdownSelector);
                $(dropdownSelector).val(prevAllowed);
                self.loadAllScreenshots();
            });
        });
    };
    


}//end ResultViewerGUI


function getImagePaths(options){
    //returns a list of image paths to show.  
    var static_url = options["static_url"];
    var folder = options["dirs"][0];
    var imageDropDownValue = getDropDownValue("#Image");
    var showOrg = getTickBoxValue("#showOrg");
    var showRes = getTickBoxValue("#showRes");
    var imagePaths = [static_url+folder+"/"+imageDropDownValue]; 
    return imagePaths;
};

function getDropDownValue(id){
    //Get the text which is currently selected
    return $(id + " option:selected").val();
};

function getTickBoxValue(id){
    //Get the text which is currently selected
    
    return $(id).is(":checked");
};


//======================== end GUI (creating html elements) ========================================================


//======================== end hooking functions to GUI element ========================================================


//======================== functions ===================================================================================
// Anything called while interacting with the GUI



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
                    var resultImageId = paramsToId(paramsCurrent); //get unique html id based on these params
                    var container = $("#" + resultImageId + " .resultImage");
                    container.empty(); //remove loading animation

                    if (isUrl(data)) {  //check whether string returned is actually an url. If not it is an error message
                        container.append(htmlImage(data, width));

                    } else {
                        container.append(htmlImageError(data, width));
                    }
                });

        var resultImageId = paramsToId(paramsCurrent);  //get unique html id based on these params
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

    var seen = {};
    var cleaned = [];
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
    
    var cleaned = [];
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
    output = cleanResultName(output);//for vessel12 this makes the names more pallatable

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
        clean = clean.slice(15);
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

    imageLink.append(image);

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
    
    return allowedScanArray.sort(isGreaterThan);

}

//for sorting numbers using sort.. why is this not built in?
function isGreaterThan(a,b){

    return a-b; //return positive if a is greater than b.
}


//returns true if this element is found inside current page.
function htmlTagExists(htmlTag){
    return $(htmlTag).length >= 1;
    
}

//checks the given dropdown item id for the name of the next option
function giveNextDropdownValueName(dropDownId){
    next = $(dropDownId + " option:selected").next().val();
    if(next === undefined){
        next = $(dropDownId).val(); //if next item does not exist, stay at current item
    };
    return next;

}

function givePrevDropdownValueName(dropDownId){
    prev = $(dropDownId + " option:selected").prev().val();
    if(prev === undefined){
        prev = $(dropDownId).val(); //if next item does not exist, stay at current item
    };

    return prev;

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

//======================== urlify, for making html safe strings from anything ==============================================

var LATIN_MAP = {
    'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A', 'Æ': 'AE', 'Ç':
    'C', 'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'Ì': 'I', 'Í': 'I', 'Î': 'I',
    'Ï': 'I', 'Ð': 'D', 'Ñ': 'N', 'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö':
    'O', 'Ő': 'O', 'Ø': 'O', 'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U', 'Ű': 'U',
    'Ý': 'Y', 'Þ': 'TH', 'Ÿ': 'Y', 'ß': 'ss', 'à':'a', 'á':'a', 'â': 'a', 'ã':
    'a', 'ä': 'a', 'å': 'a', 'æ': 'ae', 'ç': 'c', 'è': 'e', 'é': 'e', 'ê': 'e',
    'ë': 'e', 'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i', 'ð': 'd', 'ñ': 'n', 'ò':
    'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ő': 'o', 'ø': 'o', 'ù': 'u',
    'ú': 'u', 'û': 'u', 'ü': 'u', 'ű': 'u', 'ý': 'y', 'þ': 'th', 'ÿ': 'y'
};
var LATIN_SYMBOLS_MAP = {
    '©':'(c)'
};
var GREEK_MAP = {
    'α':'a', 'β':'b', 'γ':'g', 'δ':'d', 'ε':'e', 'ζ':'z', 'η':'h', 'θ':'8',
    'ι':'i', 'κ':'k', 'λ':'l', 'μ':'m', 'ν':'n', 'ξ':'3', 'ο':'o', 'π':'p',
    'ρ':'r', 'σ':'s', 'τ':'t', 'υ':'y', 'φ':'f', 'χ':'x', 'ψ':'ps', 'ω':'w',
    'ά':'a', 'έ':'e', 'ί':'i', 'ό':'o', 'ύ':'y', 'ή':'h', 'ώ':'w', 'ς':'s',
    'ϊ':'i', 'ΰ':'y', 'ϋ':'y', 'ΐ':'i',
    'Α':'A', 'Β':'B', 'Γ':'G', 'Δ':'D', 'Ε':'E', 'Ζ':'Z', 'Η':'H', 'Θ':'8',
    'Ι':'I', 'Κ':'K', 'Λ':'L', 'Μ':'M', 'Ν':'N', 'Ξ':'3', 'Ο':'O', 'Π':'P',
    'Ρ':'R', 'Σ':'S', 'Τ':'T', 'Υ':'Y', 'Φ':'F', 'Χ':'X', 'Ψ':'PS', 'Ω':'W',
    'Ά':'A', 'Έ':'E', 'Ί':'I', 'Ό':'O', 'Ύ':'Y', 'Ή':'H', 'Ώ':'W', 'Ϊ':'I',
    'Ϋ':'Y'
};
var TURKISH_MAP = {
    'ş':'s', 'Ş':'S', 'ı':'i', 'İ':'I', 'ç':'c', 'Ç':'C', 'ü':'u', 'Ü':'U',
    'ö':'o', 'Ö':'O', 'ğ':'g', 'Ğ':'G'
};
var RUSSIAN_MAP = {
    'а':'a', 'б':'b', 'в':'v', 'г':'g', 'д':'d', 'е':'e', 'ё':'yo', 'ж':'zh',
    'з':'z', 'и':'i', 'й':'j', 'к':'k', 'л':'l', 'м':'m', 'н':'n', 'о':'o',
    'п':'p', 'р':'r', 'с':'s', 'т':'t', 'у':'u', 'ф':'f', 'х':'h', 'ц':'c',
    'ч':'ch', 'ш':'sh', 'щ':'sh', 'ъ':'', 'ы':'y', 'ь':'', 'э':'e', 'ю':'yu',
    'я':'ya',
    'А':'A', 'Б':'B', 'В':'V', 'Г':'G', 'Д':'D', 'Е':'E', 'Ё':'Yo', 'Ж':'Zh',
    'З':'Z', 'И':'I', 'Й':'J', 'К':'K', 'Л':'L', 'М':'M', 'Н':'N', 'О':'O',
    'П':'P', 'Р':'R', 'С':'S', 'Т':'T', 'У':'U', 'Ф':'F', 'Х':'H', 'Ц':'C',
    'Ч':'Ch', 'Ш':'Sh', 'Щ':'Sh', 'Ъ':'', 'Ы':'Y', 'Ь':'', 'Э':'E', 'Ю':'Yu',
    'Я':'Ya'
};
var UKRAINIAN_MAP = {
    'Є':'Ye', 'І':'I', 'Ї':'Yi', 'Ґ':'G', 'є':'ye', 'і':'i', 'ї':'yi', 'ґ':'g'
};
var CZECH_MAP = {
    'č':'c', 'ď':'d', 'ě':'e', 'ň': 'n', 'ř':'r', 'š':'s', 'ť':'t', 'ů':'u',
    'ž':'z', 'Č':'C', 'Ď':'D', 'Ě':'E', 'Ň': 'N', 'Ř':'R', 'Š':'S', 'Ť':'T',
    'Ů':'U', 'Ž':'Z'
};
var POLISH_MAP = {
    'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z',
    'ż':'z', 'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S',
    'Ź':'Z', 'Ż':'Z'
};
var LATVIAN_MAP = {
    'ā':'a', 'č':'c', 'ē':'e', 'ģ':'g', 'ī':'i', 'ķ':'k', 'ļ':'l', 'ņ':'n',
    'š':'s', 'ū':'u', 'ž':'z', 'Ā':'A', 'Č':'C', 'Ē':'E', 'Ģ':'G', 'Ī':'I',
    'Ķ':'K', 'Ļ':'L', 'Ņ':'N', 'Š':'S', 'Ū':'U', 'Ž':'Z'
};
var ARABIC_MAP = {
    'أ':'a', 'ب':'b', 'ت':'t', 'ث': 'th', 'ج':'g', 'ح':'h', 'خ':'kh', 'د':'d',
    'ذ':'th', 'ر':'r', 'ز':'z', 'س':'s', 'ش':'sh', 'ص':'s', 'ض':'d', 'ط':'t',
    'ظ':'th', 'ع':'aa', 'غ':'gh', 'ف':'f', 'ق':'k', 'ك':'k', 'ل':'l', 'م':'m',
    'ن':'n', 'ه':'h', 'و':'o', 'ي':'y'
};
var LITHUANIAN_MAP = {
    'ą':'a', 'č':'c', 'ę':'e', 'ė':'e', 'į':'i', 'š':'s', 'ų':'u', 'ū':'u',
    'ž':'z',
    'Ą':'A', 'Č':'C', 'Ę':'E', 'Ė':'E', 'Į':'I', 'Š':'S', 'Ų':'U', 'Ū':'U',
    'Ž':'Z'
};
var SERBIAN_MAP = {
    'ђ':'dj', 'ј':'j', 'љ':'lj', 'њ':'nj', 'ћ':'c', 'џ':'dz', 'đ':'dj',
    'Ђ':'Dj', 'Ј':'j', 'Љ':'Lj', 'Њ':'Nj', 'Ћ':'C', 'Џ':'Dz', 'Đ':'Dj'
};
var AZERBAIJANI_MAP = {
    'ç':'c', 'ə':'e', 'ğ':'g', 'ı':'i', 'ö':'o', 'ş':'s', 'ü':'u',
    'Ç':'C', 'Ə':'E', 'Ğ':'G', 'İ':'I', 'Ö':'O', 'Ş':'S', 'Ü':'U'
};

var ALL_DOWNCODE_MAPS = [
    LATIN_MAP,
    LATIN_SYMBOLS_MAP,
    GREEK_MAP,
    TURKISH_MAP,
    RUSSIAN_MAP,
    UKRAINIAN_MAP,
    CZECH_MAP,
    POLISH_MAP,
    LATVIAN_MAP,
    ARABIC_MAP,
    LITHUANIAN_MAP,
    SERBIAN_MAP,
    AZERBAIJANI_MAP
];

var Downcoder = {
    'Initialize': function() {
        if (Downcoder.map) { // already made
            return;
        }
        Downcoder.map = {};
        Downcoder.chars = [];
        for (var i=0; i<ALL_DOWNCODE_MAPS.length; i++) {
            var lookup = ALL_DOWNCODE_MAPS[i];
            for (var c in lookup) {
                if (lookup.hasOwnProperty(c)) {
                    Downcoder.map[c] = lookup[c];
                }
            }
        }
        for (var k in Downcoder.map) {
            if (Downcoder.map.hasOwnProperty(k)) {
                Downcoder.chars.push(k);
            }
        }
        Downcoder.regex = new RegExp(Downcoder.chars.join('|'), 'g');
    }
};

function downcode(slug) {
    Downcoder.Initialize();
    return slug.replace(Downcoder.regex, function(m) {
        return Downcoder.map[m];
    });
}


function URLify(s, num_chars) {
    // changes, e.g., "Petty theft" to "petty_theft"
    // remove all these words from the string before urlifying
    s = downcode(s);
    var removelist = [
        "a", "an", "as", "at", "before", "but", "by", "for", "from", "is",
        "in", "into", "like", "of", "off", "on", "onto", "per", "since",
        "than", "the", "this", "that", "to", "up", "via", "with"
    ];
    var r = new RegExp('\\b(' + removelist.join('|') + ')\\b', 'gi');
    s = s.replace(r, '');
    // if downcode doesn't hit, the char will be stripped here
    s = s.replace(/[^-\w\s]/g, ''); // remove unneeded chars
    s = s.replace(/^\s+|\s+$/g, ''); // trim leading/trailing spaces
    s = s.replace(/[-\s]+/g, '-'); // convert spaces to hyphens
    s = s.toLowerCase(); // convert to lowercase
    return s.substring(0, num_chars);// trim to first num_chars chars
}


//======================== end functions ===================================================================================