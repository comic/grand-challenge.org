const el = document.getElementById('itk');
const files = [el.dataset.url];
const use2D = el.dataset.is2d === "True";
itkVtkViewer.createViewerFromUrl(el, {files, use2D}).then(viewer => {
    viewer.setBackgroundColor([0, 0, 0]);
    viewer.setUICollapsed(true);
    viewer.setUnits('mm');
    viewer.setRotateEnabled(false);

    if (viewer.renderWindow && viewer.renderWindow.render) {
        viewer.renderWindow.render()
    }
});
