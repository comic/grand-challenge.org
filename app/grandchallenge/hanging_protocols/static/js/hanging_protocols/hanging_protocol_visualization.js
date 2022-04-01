function insertAfter(newNode, existingNode) {
    existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}

function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}

function showOrHideVisualizationDiv(jsonString) {
    console.log(jsonString)
    if (jsonString != '' && jsonString != 'null') {
            console.log("show!")
            document.getElementById("hpVisualization").style.display = 'block';
        } else {
            document.getElementById("hpVisualization").style.display = 'none';
    }
}

function getGridDimensions(json) {
    let allX = [];
    let allY = [];
    let allW = [];
    let allH = [];

    for (let i = 0; i < json.length; i++) {
        allX.push(json[i].x);
        allY.push(json[i].y);
        allW.push(json[i].w);
        allH.push(json[i].h);
    }

    let totalWidth = Math.max(...allX.map(function(num, idx) {return num+allW[idx]}));
    let totalHeight = Math.max(...allY.map(function(num, idx) {return num+allH[idx]}));

    return [totalHeight, totalWidth]
}

function createViewportDiv(viewportSpec, totalHeight, totalWidth) {
    let viewportDiv = document.createElement("div");
    viewportDiv.setAttribute('id', viewportSpec.viewport_name);
    viewportDiv.style.opacity = '0.5';
    viewportDiv.style.position = 'absolute';
    viewportDiv.style.zIndex = '-' + viewportSpec.order;
    viewportDiv.style.width = (viewportSpec.w / parseFloat(totalWidth).toFixed(2))*100 + '%';
    viewportDiv.style.height = (viewportSpec.h / parseFloat(totalHeight).toFixed(2))*100 + '%';
    viewportDiv.style.left = (viewportSpec.x / parseFloat(totalWidth).toFixed(2))*100 + '%';
    viewportDiv.style.top = (viewportSpec.y / parseFloat(totalHeight).toFixed(2))*100 + '%';
    document.getElementById("hpVisualization").appendChild(viewportDiv).classList.add('bg-dark', 'rounded', 'border', 'border-2', 'd-flex', 'flex-column', 'justify-content-center', 'align-items-center');

    viewportDiv.innerHTML += '<h4>'+ viewportSpec.viewport_name + '</h4>';
    if (viewportSpec.fullsizable == true) {
        viewportDiv.innerHTML += '<i class="fas fa-expand m-1"></i>'
    }
}

function updateHangingProtocolVisualization(jsonString){
    jsonString = jsonString || document.getElementById("id_json").value;
    showOrHideVisualizationDiv(jsonString);
    try {
        let jsonSpec = JSON.parse(jsonString);
        [totalHeight, totalWidth] = getGridDimensions(jsonSpec);
        removeAllChildNodes(document.getElementById("hpVisualization"));
        for (let i = 0; i < jsonSpec.length; i++) {
            createViewportDiv(jsonSpec[i], totalHeight, totalWidth);
        }
    } catch (err) {
    }
}

$(document).ready(function () {
    if (window.location.href.includes("update") | window.location.href.includes("create")) {
        let jsonString = document.getElementById("id_json").value;
        showOrHideVisualizationDiv(jsonString);
        updateHangingProtocolVisualization(jsonString);
        document.getElementById('jsoneditor_id_json').addEventListener('input', function(){updateHangingProtocolVisualization()});
        document.getElementById('jsoneditor_id_json').addEventListener('keyup', function(){updateHangingProtocolVisualization()});
        document.getElementById('jsoneditor_id_json').addEventListener('paste', function(){updateHangingProtocolVisualization()});
    } else {
        let jsonString = document.getElementById("id_json").innerHTML;
        showOrHideVisualizationDiv(jsonString);
        updateHangingProtocolVisualization(jsonString);
    }
});
