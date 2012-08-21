from django.template import Context, loader
from django.http import HttpResponse


def index(request):
    t = loader.get_template('mevislab_visualisation/index.html')
    c = Context({
        'app': 'liver',
    })
    return HttpResponse(t.render(c))
