
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
    const containers = document.getElementsByClassName("nav-tab-dropdown-container");

    const ulDropdownClasses = ["dropdown-menu", "dropdown-menu-left"];
    const ulTabClasses = ["nav", "nav-tabs", "border-0"];
    const itemDropdownClasses = ["dropdown-item", "challengeDropdown"];
    const itemTabClasses = ["nav-item"];

    // Change the classes
    for (let container of containers) {
        let ul  = container.querySelector("ul");

        if (reverse === true) {
            container.classList.remove("dropdown");

            ul.classList.add(...ulTabClasses);
            ul.classList.remove(...ulDropdownClasses);
        }
        else {
            container.classList.add("dropdown");

            ul.classList.add(...ulDropdownClasses);
            ul.classList.remove(...ulTabClasses);
        }

        let items = container.querySelectorAll("li");

        for (let item of items) {
            if (reverse === true) {
                item.classList.add(...itemTabClasses);
                item.classList.remove(...itemDropdownClasses);
            } else {
                item.classList.add(...itemDropdownClasses);
                item.classList.remove(...itemTabClasses);
            }
        }
    }
}

window.addEventListener('resize', handle_nav_tab_dropdown);

handle_nav_tab_dropdown();
