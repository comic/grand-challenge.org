function insertAfter(newNode, existingNode) {
    existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}

function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}

function showOrHideVisualizationDiv(divId, jsonString) {
    if (jsonString != '' && jsonString != 'null') {
            document.getElementById(divId).style.display = 'block';
        } else {
            document.getElementById(divId).style.display = 'none';
    }
}

function getGridDimensions(json) {
    let allX = [];
    let allY = [];
    let allW = [];
    let allH = [];

    for (let i = 0; i < json.length; i++) {
        json[i].x == undefined ? undefined : allX.push(json[i].x);
        json[i].y == undefined ? undefined : allY.push(json[i].y);
        json[i].w == undefined ? undefined : allW.push(json[i].w);
        json[i].h == undefined ? undefined : allH.push(json[i].h);
    }
    let totalWidth = (allX.length != json.length | allW.length != json.length) ? json.length : Math.max(...allX.map(function(num, idx) {return num+allW[idx]}));
    let totalHeight = (allY.length != json.length | allH.length != json.length) ? 1 : Math.max(...allY.map(function(num, idx) {return num+allH[idx]}));

    return [totalHeight, totalWidth]
}

function createViewportDiv(divId, viewportNum, viewportSpec, totalHeight, totalWidth) {
    let viewportDiv = document.createElement("div");
    viewportDiv.setAttribute('id', viewportSpec.viewport_name);
    viewportDiv.style.opacity = '0.5';
    viewportDiv.style.position = 'absolute';
    viewportDiv.style.zIndex = '-' + viewportSpec.order;
    viewportDiv.style.width = isNaN(viewportSpec.w) ? (1 / parseFloat(totalWidth).toFixed(2))*100 + '%' : (viewportSpec.w / parseFloat(totalWidth).toFixed(2))*100 + '%';
    viewportDiv.style.height = isNaN(viewportSpec.h) ? "100%" : (viewportSpec.h / parseFloat(totalHeight).toFixed(2))*100 + '%';
    viewportDiv.style.left = isNaN(viewportSpec.x) ? (viewportNum / parseFloat(totalWidth).toFixed(2))*100 + '%' : (viewportSpec.x / parseFloat(totalWidth).toFixed(2))*100 + '%';
    viewportDiv.style.top = isNaN(viewportSpec.y) ? "0%" : (viewportSpec.y / parseFloat(totalHeight).toFixed(2))*100 + '%';
    document.getElementById(divId).appendChild(viewportDiv).classList.add('bg-dark', 'rounded', 'border', 'border-2', 'd-flex', 'flex-column', 'justify-content-center', 'align-items-center');

    viewportDiv.innerHTML += '<p style="font-size: 1.5em">'+ viewportSpec.viewport_name + '</p>';
    if (viewportSpec.fullsizable == true) {
        viewportDiv.innerHTML += '<i class="fas fa-expand m-1"></i>'
    }
}

function updateHangingProtocolVisualization(parentDivId, jsonString){
    jsonString = jsonString || document.getElementById("id_json").value;
    parentDivId = parentDivId || "hpVisualization";
    showOrHideVisualizationDiv(parentDivId, jsonString);
    try {
        let jsonSpec = JSON.parse(jsonString);
        [totalHeight, totalWidth] = getGridDimensions(jsonSpec);
        console.log(totalWidth, totalHeight)
        removeAllChildNodes(document.getElementById(parentDivId));
        for (let i = 0; i < jsonSpec.length; i++) {
            createViewportDiv(parentDivId, i, jsonSpec[i], totalHeight, totalWidth);
        }
    } catch (err) {
    }
}

$(document).ready(function () {
    if (window.location.href.includes("update") | window.location.href.includes("create")) {
        let jsonString = document.getElementById("id_json").value;
        showOrHideVisualizationDiv("hpVisualization", jsonString);
        updateHangingProtocolVisualization("hpVisualization", jsonString);
        document.getElementById('jsoneditor_id_json').addEventListener('input', function(){updateHangingProtocolVisualization()});
        document.getElementById('jsoneditor_id_json').addEventListener('keyup', function(){updateHangingProtocolVisualization()});
        document.getElementById('jsoneditor_id_json').addEventListener('paste', function(){updateHangingProtocolVisualization()});
    } else {
        let jsonDivs = document.querySelectorAll("[id^='id_json']");
        let hpVizDivs = document.querySelectorAll("[id^='hpVisualization']");
        for (let i = 0; i < jsonDivs.length; i++) {
            let jsonString = jsonDivs[i].innerHTML;
            showOrHideVisualizationDiv(hpVizDivs[i].id, jsonString);
            updateHangingProtocolVisualization(hpVizDivs[i].id, jsonString);
        }
    }
});
