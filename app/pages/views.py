from django.shortcuts import render

# Create your views here.
from comicsite.views import site_get_standard_vars, getRenderedPageIfAllowed


def page(request, site_short_name, page_title):
    """ show a single page on a site """

    [site, pages, metafooterpages] = site_get_standard_vars(site_short_name)
    currentpage = getRenderedPageIfAllowed(page_title, request, site)
    response = render(request, 'page.html', {'currentpage': currentpage})

    # TODO: THis has code smell. If page has to be checked like this, is it
    # ok to use a page object for error messages?
    if hasattr(currentpage, "is_error_page"):
        if currentpage.is_error_page:
            response.status_code = 403

    return response