possibleViewPorts =  JSON.parse(document.getElementById('possibleViewPorts').textContent);

function insertAfter(newNode, existingNode) {
    existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}

function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}

function showOrHideVisualizationDiv(divId, jsonString) {
    if (jsonString !== '' && jsonString !== 'null') {
            document.getElementById(divId).style.display = 'block';
        } else {
            document.getElementById(divId).style.display = 'none';
    }
}

function getGridDimensions(json) {
    const dims = { x: [], y: [], w: [], h: [] };

    for (const viewport of json) {
      for (const d of Object.keys(dims)) {
        if (d in viewport) {
          dims[d].push(viewport[d]);
        }
      }
    }

    let totalWidth = (dims.x.length !== json.length || dims.w.length !== json.length) ? json.length : Math.max(...dims.x.map(function(num, idx) {return num+dims.w[idx]}));
    let totalHeight = (dims.y.length !== json.length || dims.h.length !== json.length) ? 1 : Math.max(...dims.y.map(function(num, idx) {return num+dims.h[idx]}));

    return [totalHeight, totalWidth]
}

function createViewportDiv(divId, viewportNum, viewportSpec, totalHeight, totalWidth) {
    let viewportDiv = document.createElement("div");
    viewportDiv.setAttribute('id', viewportSpec.viewport_name);
    if (possibleViewPorts.includes(viewportSpec.viewport_name)) {
        viewportDiv.style.background = '#7b8a8b';
    } else {
        viewportDiv.style.background = '#e74c3c';
    }
    viewportDiv.style.opacity = '0.5';
    viewportDiv.style.position = 'absolute';
    viewportDiv.style.fontSize = '1.5em';
    viewportDiv.style.zIndex = 20 - viewportSpec.order;
    viewportDiv.style.width = isNaN(viewportSpec.w) ? (1 / parseFloat(totalWidth) * 100).toFixed(2) + '%' : (viewportSpec.w / parseFloat(totalWidth) * 100).toFixed(2) + '%';
    viewportDiv.style.height = isNaN(viewportSpec.h) ? "100%" : (viewportSpec.h / parseFloat(totalHeight) * 100).toFixed(2) + '%';
    viewportDiv.style.left = isNaN(viewportSpec.x) ? (viewportNum / parseFloat(totalWidth) * 100).toFixed(2) + '%' : (viewportSpec.x / parseFloat(totalWidth) * 100).toFixed(2) + '%';
    viewportDiv.style.top = isNaN(viewportSpec.y) ? "0%" : (viewportSpec.y / parseFloat(totalHeight) * 100).toFixed(2) + '%';
    document.getElementById(divId).appendChild(viewportDiv).classList.add('rounded', 'border', 'border-2', 'd-flex', 'flex-column', 'justify-content-center', 'align-items-center');

    if (!possibleViewPorts.includes(viewportSpec.viewport_name)) {
        viewportDiv.innerHTML += '<p class="mb-0" style="color: #fff">Invalid viewport name</p>';
    } else {
        viewportDiv.innerHTML += '<p class="mb-0">' + viewportSpec.viewport_name + '</p>';
        if (viewportSpec.fullsizable) {
            viewportDiv.innerHTML += '<i class="fas fa-expand"></i>'
        }
    }
}

function updateHangingProtocolVisualization(parentDivId, jsonString){
    jsonString = jsonString || document.getElementById("id_json").value;
    parentDivId = parentDivId || "hpVisualization";
    showOrHideVisualizationDiv(parentDivId, jsonString);
    try {
        let jsonSpec = JSON.parse(jsonString);
        let validJsonSpec = jsonSpec.filter(viewPort => typeof viewPort.viewport_name !== "undefined");
        [totalHeight, totalWidth] = getGridDimensions(validJsonSpec);
        removeAllChildNodes(document.getElementById(parentDivId));
        for (let i = 0; i < validJsonSpec.length; i++) {
            createViewportDiv(parentDivId, i, validJsonSpec[i], totalHeight, totalWidth);
        }
    } catch (err) {
    }
}
