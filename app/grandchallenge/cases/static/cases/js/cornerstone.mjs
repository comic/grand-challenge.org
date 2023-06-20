const SITK_PIXEL_TYPE_TO_BIT_DEPTH = new Map([
    [itk.IntTypes.UInt8, 8],
    [itk.IntTypes.Int8, 8],
    [itk.IntTypes.UInt16, 16],
    [itk.IntTypes.Int16, 16],
    [itk.IntTypes.UInt32, 32],
    [itk.IntTypes.Int32, 32],
    [itk.IntTypes.UInt64, 64],
    [itk.IntTypes.Int64, 64],
    [itk.FloatTypes.Float32, 32],
    [itk.FloatTypes.Float64, 64],
]);

const imagePk = JSON.parse(document.getElementById('imagePk').textContent);
const imageId = `grandChallengeLoader://${imagePk}`;
const loadingEl = document.getElementById('loading');
const element = document.getElementById('itkImage');

function itkBlobToCsImage(itkBlob, imageObj) {
    if (imageObj.color_space === "YCBCR") {
        throw Error('Unsupported color space: YCBCR');
    }
    const file = new File([itkBlob], 'image.mha');
    return itk.readFile(null, file).then(function ({image, mesh, polyData, webWorker}) {
        if (!SITK_PIXEL_TYPE_TO_BIT_DEPTH.has(image.imageType.componentType)) {
            throw Error('Unsupported ITK image type: ' + image.imageType.componentType);
        }
        const bitDepth = SITK_PIXEL_TYPE_TO_BIT_DEPTH.get(image.imageType.componentType);
        let imageData = image.data;


        imageObj.color = ['RGB', 'RGBA'].includes(imageObj.color_space);
        if (imageObj.color_space === 'RGB') {
            // convert RGB to RGBA
            const newLength = imageData.length + imageData.length / 3;
            const rgbaArr = new imageData.constructor(newLength);
            for (let i = 0; i < imageData.length / 3; i++) {
                rgbaArr[i * 4] = imageData[i * 3];
                rgbaArr[i * 4 + 1] = imageData[i * 3 + 1];
                rgbaArr[i * 4 + 2] = imageData[i * 3 + 2];
                rgbaArr[i * 4 + 3] = 2 ** bitDepth;
            }
            imageData = rgbaArr;
            imageObj.rgba = true;
        }

        // Finding actual min/max pixel values cannot be done because
        // using Math.min(...pixelValues) will exceed max call stack
        // size for large images. We use a simple heuristic to find
        // theoretical min/max values for this pixel type.
        imageObj.maxPixelValue = 2 ** bitDepth / 2;
        imageObj.minPixelValue = -imageObj.maxPixelValue;
        if (image.imageType.componentType.includes('uint')) {
            imageObj.minPixelValue = 0;
            imageObj.maxPixelValue = 2 ** bitDepth;
        }
        imageObj.sizeInBytes = imageData.length * bitDepth / 8;
        imageObj.windowWidth = imageObj.window_width ?? (imageObj.maxPixelValue - imageObj.minPixelValue);
        imageObj.windowCenter = imageObj.window_center ?? imageObj.minPixelValue + imageObj.windowWidth / 2;
        imageObj.columnPixelSpacing = image.spacing[0];
        imageObj.rowPixelSpacing = image.spacing[1];
        imageObj.rows = imageObj.height;
        imageObj.columns = imageObj.width;
        imageObj.imageId = imageId;
        imageObj.slope = 1;
        imageObj.intercept = 0;
        imageObj.invert = false;
        imageObj.getPixelData = () => imageData;
        webWorker.terminate();
        return imageObj;
    });
}

// Register grand challenge image loader
cornerstone.registerImageLoader('grandChallengeLoader', (imageId) => {
    const [gc, imagePk] = imageId.split('://');
    const url = `/api/v1/cases/images/${imagePk}/`;
    return {
        promise: new Promise((resolve, reject) => {
            fetch(url).then(r => {
                if (r.status === 200) {
                    return r.json()
                } else {
                    throw Error(`Fetch error: ${r.statusText}`);
                }
            }).then(imageObj => {
                const mhFiles = imageObj.files.filter(f => ["MHD", "MHA"].includes(f.image_type));
                if (mhFiles.length < 1) {
                    throw Error('No MHD/MHA files found for image.');
                }
                return fetch(mhFiles[0].file).then(r => {
                    if (r.status === 200) {
                        return r.blob();
                    } else {
                        reject(`Fetch error: ${r.text()}`);
                    }
                }).then(itkBlob => {
                    itkBlobToCsImage(itkBlob, imageObj).then(csImage => {
                        resolve(csImage)
                    });
                });
            }).catch(e => reject(e));
        }),
    };
});

// setup handlers before we display the image
element.addEventListener('cornerstoneimagerendered', e => {
    const eventData = e.detail;
    console.log("Render Time:" + eventData.renderTimeInMs + " ms");
    // set the canvas context to the image coordinate system
    cornerstone.setToPixelCoordinateSystem(eventData.enabledElement, eventData.canvasContext);
    document.getElementById('bottomright').textContent = "Window level: " + Math.round(eventData.viewport.voi.windowWidth) + "/" + Math.round(eventData.viewport.voi.windowCenter) + ", Zoom: " + eventData.viewport.scale.toFixed(2);
});

// Initialize viewport element
cornerstone.enable(element, {
    renderer: 'webgl',
    desynchronized: true,
    preserveDrawingBuffer: true
});

// load and display the image
cornerstone.loadAndCacheImage(imageId).then(function (image) {
    const viewport = cornerstone.getViewport(element);
    cornerstone.displayImage(element, image, viewport);
    const {pixelData, getPixelData, ...restImage} = image;
    return restImage;
}).then(function (image) {
    loadingEl.style.display = 'none';
    $('[data-toggle="tooltip"]').tooltip();

    // add event handlers to pan/windowlevel/zoom image on mouse move
    element.addEventListener('mousedown', function (e) {
        let lastX = e.pageX;
        let lastY = e.pageY;

        function mouseMoveHandler(e) {
            const deltaX = e.pageX - lastX;
            const deltaY = e.pageY - lastY;
            lastX = e.pageX;
            lastY = e.pageY;
            const viewport = cornerstone.getViewport(element);
            if (e.which === 2) {
                const maxWindowWidth = image.maxPixelValue - image.minPixelValue;
                viewport.voi.windowWidth += deltaX / element.clientHeight * maxWindowWidth;
                viewport.voi.windowCenter += deltaY / element.clientWidth * maxWindowWidth;
            } else if (e.which === 1) {
                viewport.translation.x += deltaX / viewport.scale;
                viewport.translation.y += deltaY / viewport.scale / 2;
            } else if (e.which === 3) {
                viewport.scale += (deltaY / 100);
            }
            cornerstone.setViewport(element, viewport);
        }

        function mouseUpHandler() {
            document.body.style.cursor = 'default';
            document.removeEventListener('mouseup', mouseUpHandler);
            document.removeEventListener('mousemove', mouseMoveHandler);
        }

        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
    });


    // Add button toolbar manipulation events
    function manipulateViewport(element, manipulationFn) {
        let viewport = cornerstone.getViewport(element);
        viewport = manipulationFn(viewport);
        cornerstone.setViewport(element, viewport);
    }

    document.getElementById('invert').addEventListener('click', function (e) {
        manipulateViewport(element, vp => ({...vp, invert: !vp.invert}));
    });
    document.getElementById('hflip').addEventListener('click', function (e) {
        manipulateViewport(element, vp => ({...vp, hflip: !vp.hflip}));
    });
    document.getElementById('vflip').addEventListener('click', function (e) {
        manipulateViewport(element, vp => ({...vp, vflip: !vp.vflip}));
    });
    document.getElementById('rotate').addEventListener('click', function (e) {
        manipulateViewport(element, vp => ({...vp, rotation: vp.rotation + 90}));
    });

    // Show world coordinate values on mousemove
    element.addEventListener('mousemove', function (event) {
        const pixelCoords = cornerstone.pageToPixel(element, event.pageX, event.pageY);
        document.getElementById('bottomleft').textContent = "X=" + pixelCoords.x + ", Y=" + pixelCoords.y;
    });
});
