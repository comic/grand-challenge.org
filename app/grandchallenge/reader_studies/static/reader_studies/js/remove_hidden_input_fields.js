form_id = document.getElementById("form-id").dataset.formid
document.querySelector('#form-'+form_id).addEventListener("submit", function(e){
    // this removes the hidden interface input fields that flexible-image-widget.html and image-search-widget.html add
    // to prevent multiple interface values from being submitted with the form
    var elements = document.getElementsByClassName("current-interface-slug");
    while (elements.length > 0) {
        elements[0].remove()
    }
});
