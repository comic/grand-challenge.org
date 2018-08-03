import copy
import datetime

from django.utils import timezone
from xlrd import open_workbook

from grandchallenge.challenges.models import logger, Challenge


class ProjectExcelReader(object):
    """ Records on challenges from grand-challenge.org are kept in an xls file
    This had the advantages of easy copy-pasting and quick simple and flexible
    editing and statistics. This class reads the grand-challenge xls file and
    renders html for each challenge found.
    
    TODO: This class combines functionality which should probably be separate:
    read xls, render projectlink to html etc. Split later.
    """

    def __init__(self, path, sheetname):
        self.path = path
        self.sheetname = sheetname

    def get_project_links(self):
        """ Read excel file and with challenge listings and return an array of
        projectlinks describing each 
        """
        book = open_workbook(self.path)
        sheet = book.sheet_by_name(self.sheetname)
        items = self.get_excel_items(sheet)
        projectlinks = []
        for item in items:
            if item["abreviation"] != "":
                projectlink = ProjectLink(item)
                projectlinks.append(projectlink)
        book.unload_sheet(self.sheetname)
        return projectlinks

    def get_excel_items(self, sheet):
        """ Treat each row in excel sheet as an item. First row in sheet should
        contain column headers. Each item returned is an object that has a
        field for each column.
        """
        items = []
        for row in range(1, sheet.nrows):  # skip first row as those are titles
            items.append(self.get_excel_item(sheet, row))
        return items

    def get_excel_item(self, sheet, row):
        """
        """
        item = {}
        col_titles = sheet.row_values(0, 0)
        col_values = sheet.row_values(row, 0)
        for (title, value) in zip(col_titles, col_values):
            if title != "":
                item[title] = value
        return item


class ProjectLink(object):
    """ Metadata about a single project: url, event etc. Used as the shared
    class for both external challenges and projects hosted on comic so they can
    be shown on the projectlinks overview page

    """
    # Using dict instead of giving a lot of fields to this object because the
    # former is easier to work with
    defaults = {
        "abreviation": "",
        "title": "",
        "description": "",
        "URL": "",
        "submission URL": "",
        "event name": "",
        "year": "",
        "event URL": "",
        "website section": "",
        "overview article url": "",
        "overview article journal": "",
        "workshop date": "",
        "open for submission": "",
        "dataset downloads": "",
        "submitted results": "",
        "last submission date": "",
        "hosted on comic": False,
        "project type": "",
    }
    # css selector used to designate a project as still open
    UPCOMING = "challenge_upcoming"

    def __init__(self, params, date=""):
        self.params = copy.deepcopy(self.defaults)
        self.params.update(params)
        # add date in addition to datestring already in dict, to make sorting
        # easier.
        if date == "":
            self.date = self.determine_project_date()
        else:
            self.date = date
        self.params["year"] = self.date.year

    def determine_project_date(self):
        """ Try to find the date for this project. Return default
        date if nothing can be parsed.

        """
        if self.params["hosted on comic"]:
            if self.params["workshop date"]:
                date = self.to_datetime(self.params["workshop date"])
            else:
                date = ""
        else:
            datestr = self.params["workshop date"]
            # this happens when excel says its a number. I dont want to force
            # the excel file to be clean, so deal with it here.
            if type(datestr) == float:
                datestr = str(datestr)[0:8]
            try:
                date = timezone.make_aware(
                    datetime.datetime.strptime(datestr, "%Y%m%d"),
                    timezone.get_default_timezone(),
                )
            except ValueError:
                logger.warning(
                    "could not parse date '%s' from xls line starting with "
                    "'%s'. Returning default date 2013-01-01" %
                    (datestr, self.params["abreviation"])
                )
                date = ""
        if date == "":
            # If you cannot find the exact date for a project,
            # use date created
            if self.params["hosted on comic"]:
                return self.params["created at"]

            # If you cannot find the exact date, try to get at least the year
            # right. again do not throw errors, excel can be dirty
            year = int(self.params["year"])
            try:
                date = timezone.make_aware(
                    datetime.datetime(year, 1, 1),
                    timezone.get_default_timezone(),
                )
            except ValueError:
                logger.warning(
                    "could not parse year '%f' from xls line starting with "
                    "'%s'. Returning default date 2013-01-01" %
                    (year, self.params["abreviation"])
                )
                date = timezone.make_aware(
                    datetime.datetime(2013, 1, 1),
                    timezone.get_default_timezone(),
                )
        return date

    def find_link_class(self):
        """ Get css classes to give to this projectlink.
        For filtering and sorting project links, we discern upcoming, active
        and inactive projects. Determiniation of upcoming/active/inactive is
        described in column 'website section' in grand-challenges xls.
        For projects hosted on comic, determine this automatically based on
        associated workshop date. If a comicsite has an associated workshop
        which is in the future, make it upcoming, otherwise active

        """
        linkclass = Challenge.CHALLENGE_ACTIVE
        # for project hosted on comic, try to find upcoming automatically
        if self.params["hosted on comic"]:
            linkclass = self.params["project type"]
            if self.date > self.to_datetime(datetime.datetime.today()):
                linkclass += " " + self.UPCOMING
        else:
            # else use the explicit setting in xls
            section = self.params["website section"].lower()
            if section == "upcoming challenges":
                linkclass = Challenge.CHALLENGE_ACTIVE + " " + self.UPCOMING
            elif section == "active challenges":
                linkclass = Challenge.CHALLENGE_ACTIVE
            elif section == "past challenges":
                linkclass = Challenge.CHALLENGE_INACTIVE
            elif section == "data publication":
                linkclass = Challenge.DATA_PUB
        return linkclass

    @staticmethod
    def to_datetime(date):
        """ add midnight to a date to make it a datetime because I cannot
        compare these two types directly. Also add offset awareness to easily
        compare with other django datetimes.
        """
        dt = datetime.datetime(date.year, date.month, date.day)
        return timezone.make_aware(dt, timezone.get_default_timezone())

    def is_hosted_on_comic(self):
        return self.params["hosted on comic"]
