function updatePhaseNavbar() {
    let navWidth = 0;
    const dropdownMenu = $("#phaseNavbarDropdownMenu");
    const phaseNavItems = $(
        "#phaseNavbarUl > li:not(#phaseNavbarDropdownMenu)",
    );
    const dropdownMenuWidth = dropdownMenu.outerWidth(false);
    phaseNavItems.each(function () {
        navWidth += $(this).outerWidth(false);
    });
    const availableSpace =
        $("#phaseNavbar").outerWidth(true) - dropdownMenuWidth;

    if (navWidth > availableSpace) {
        const lastItem = phaseNavItems.last();
        lastItem.attr("data-width", lastItem.outerWidth(true));
        lastItem.prependTo($("#phaseNavbarDropdownMenu ul"));
        updatePhaseNavbar();
    } else {
        const firstMoreElement = $("#phaseNavbarDropdownMenu ul li").first();
        if (navWidth + firstMoreElement.data("width") < availableSpace) {
            firstMoreElement.insertBefore(dropdownMenu);
            updatePhaseNavbar();
        }
    }

    if ($("#phaseNavbarDropdownMenu li").length > 0) {
        dropdownMenu.css("display", "inline-block");
    } else {
        dropdownMenu.css("display", "none");
    }
}
$(window).on("resize load", () => {
    updatePhaseNavbar();
});
