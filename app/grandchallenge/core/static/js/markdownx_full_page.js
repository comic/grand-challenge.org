$('document').ready(function(){
    // Sync the height of the preview element to the height of the editor element.
    let ELEMENTS = document.getElementsByClassName('markdownx');
    Object.values(ELEMENTS).map(function (element) {
        let editor = element.querySelector('.markdownx-editor'), preview = element.querySelector('.markdownx-preview');
        preview.style.height = editor.clientHeight + "px";
        const resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            if (entry.contentBoxSize) {
              preview.style.height = editor.clientHeight + "px";
            }
          }
        });
        resizeObserver.observe(editor);
    });
});
