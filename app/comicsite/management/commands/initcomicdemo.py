from django.conf import settings
from django.core.management import BaseCommand
from userena.models import UserenaSignup

from comicmodels.models import ComicSite, Page


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Creates the main project, demo user and demo challenge
        """
        challenge, created = ComicSite.objects.get_or_create(
            short_name=settings.MAIN_PROJECT_NAME,
            description='main project')

        if created:
            Page.objects.create(
                title='home',
                comicsite=challenge,
                html="<h1>\r\n\tDefault Page</h1>\r\n<p>\r\n\tYou almost have COMIC framework up and running. Congratulations.<br />\r\n\tFor up to date info, please visit <a href=\"https://github.com/comic/comic-django\">https://github.com/comic/comic-django</a></p>\r\n<p>\r\n\tOn COMIC framework anyone can sign up and create a project. A project is a collection of pages, data and software under a single name.<br />\r\n\tThe page you are reading now is the page \"home\" in the project \"comic\". The project \"comic\" is special in two ways:&nbsp; First, it is shown by default if you navigate to the root url and second, it's pages appear as a menu below each and every page of the framework. To make a project other than 'comic' the main project, change the MAIN_PROJECT_NAME setting in comic/settings/00_default.conf.</p>\r\n<h2>\r\n\tUseful Code</h2>\r\n<p>\r\n\tAt the base level a project in COMIC framework is a collection of html pages under a single header. Most if the interesting functionality comes from using django <em>template tags</em> which you can use as functions inside you html code. They look like { % render_graph results.csv % } and are rendered by django when encountered. A list of template tags can be found on page \"<a href=\"../template_tags\">template tags</a>\"</p>\r\n<p>\r\n\t\tcode for a sign in/ create new project button on a page:</p>\r\n<p>\r\n\t&nbsp;</p>\r\n<div style=\"text-align: center;background-color:#DFDFDF;float:none;margin-left:10px;margin-right:16px;margin-top:1px;padding:12px;width:164px;\">\r\n\t\r\n\t<p>\r\n\t\t <a class=\"createNewComicSiteLink\" href=\"{% url 'challenge_create' %}\">Create a new project</a></div>\r\n<p>There is a <a href='/site/testsite/'>test site here</a>.</p><p> <h1>Site Stats</h1><div class='row'><div class='col-sm-4'></div><div class='col-sm-4'>{% allusers_statistics False %}</div><div class='col-sm-4'></div></div> </p>\r\n",
            )

            Page.objects.create(
                title='template_tags',
                display_title='template tags',
                comicsite=challenge,
                html="<p>\r\n\tBelow is a list of all template tags which can be used on any page of the framework. For example, the table below is rendered by inserting { % taglist % } into the html of the page. Some template tags use additional arguments. These are described in the right column.</p>\r\n<p>\r\n\t&nbsp;</p>\r\n<p>\r\n\t{% taglist %}</p>\r\n<p>\r\n\t&nbsp;</p>\r\n<p>\r\n\tIn addition, any <a href=\"https://docs.djangoproject.com/en/dev/ref/templates/builtins/\">built-in django template tag</a> is also available.</p>\r\n",
            )

            Page.objects.create(
                title='all_challenges',
                display_title='all challenges',
                comicsite=challenge,
                html="{% all_projectlinks %}",
            )

            demoadmin = UserenaSignup.objects.create_user(
                username='demo', email='demo@example.com', password='demo',
                active=True,
            )

            demoparticipant = UserenaSignup.objects.create_user(
                username='demop', email='demop@example.com', password='demop',
                active=True,
            )

            demo = ComicSite.objects.create(
                short_name='demo',
                description='demo project',
                creator=demoadmin,
                use_evaluation=True,
                hidden=False
            )

            demo.add_participant(demoparticipant)

            Page.objects.create(
                comicsite=demo,
                title='all',
                permission_lvl='ALL'
            )

            Page.objects.create(
                comicsite=demo,
                title='reg',
                permission_lvl='REG'
            )

            Page.objects.create(
                comicsite=demo,
                title='adm',
                permission_lvl='ADM'
            )
