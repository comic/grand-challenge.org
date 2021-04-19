
function handle_nav_tab_dropdown() {
    if (window.innerWidth < 992) {
        // 992 px is the bootstrap breakpoint for lg
        navs_to_dropdown();
    } else {
        navs_to_dropdown(true);
    }
}

function navs_to_dropdown(reverse = false) {
    // Get all elements that need to change class
    // const tabContainers = document.getElementsByClassName("nav-tab-dropdown-container");
    const containers = document.querySelectorAll('.nav-tab-dropdown-container,.nav-pill-dropdown-container');

    const ulDropdownClasses = ["dropdown-menu", "dropdown-menu-left"];
    const ulTabClasses = ["nav", "nav-tabs", "border-0"];
    const itemDropdownClasses = ["dropdown-item", "challengeDropdown"];
    const itemTabPillClasses = ["nav-item"];
    const ulPillClasses = ["nav", "nav-pills", "col-12", "mb-3"];

    // Change the classes
    for (let container of containers) {
        let ul  = container.querySelector("ul");

        if (reverse === true) {
            container.classList.remove("dropdown");
            ul.classList.remove(...ulDropdownClasses);

            if (container.classList.contains("nav-tab-dropdown-container")) {
                ul.classList.add(...ulTabClasses);
            } else if (container.classList.contains("nav-pill-dropdown-container")) {
                ul.classList.add(...ulPillClasses);
            }
        }
        else {
            container.classList.add("dropdown");
            ul.classList.add(...ulDropdownClasses);

            if (container.classList.contains("nav-tab-dropdown-container")) {
                ul.classList.remove(...ulTabClasses);
            } else if (container.classList.contains("nav-pill-dropdown-container")) {
                ul.classList.remove(...ulPillClasses);
            }
        }

        let items = container.querySelectorAll("li");

        for (let item of items) {
            if (reverse === true) {
                item.classList.add(...itemTabPillClasses);
                item.classList.remove(...itemDropdownClasses);
            } else {
                item.classList.add(...itemDropdownClasses);
                item.classList.remove(...itemTabPillClasses);
            }
        }
    }

}

window.addEventListener('resize', handle_nav_tab_dropdown);

handle_nav_tab_dropdown();
