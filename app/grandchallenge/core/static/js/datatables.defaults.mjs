$.extend(true, DataTable.defaults, {
    scrollX: true,
    language: {
        paginate: {
            next: "Next",
            previous: "Previous",
        },
    },
    pagingType: "simple_numbers",
});

$(document).on("init.dt", () => {
    const element = $(".dt-scroll-body");

    if (element.length === 0) {
        console.warn(
            "Warning: Element for floating-scroll attachment could not be located",
        );
    }

    element.floatingScroll();
});
