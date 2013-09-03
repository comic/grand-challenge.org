from xlrd import open_workbook
from xlrd import sheet
import os


    
class ProjectExcelReader(object):
    """ Records on challenges from grand-challenge.org are kept in an xls file
    This had the advantages of easy copy-pasting and quick simple and flexible
    editing and statistics. This class reads the grand-challenge xls file and
    renders html for each challenge found.
    
    TODO: This class combines functionality which should probably be separate:
    read xls, render projectlink to html etc. Split later.
    """

    def __init__(self,path,sheetname):
        self.path = path 
        self.sheetname = sheetname
        
        
    def write_link_html(self,path=""):
        items = self.get_excel_items(self.sheet)
        links = self.get_project_links().encode("utf-8")

        if path == "":
            path = "D:/temp/links.html"
        
        f = open(path,"w")
        print ("* wrote HTML for all projects to "+path)
        f.write(links)
        f.close()
    
    def get_project_links(self):
        """ Read excel file and output html to show all challenge links
        listed there 
        """
        book = open_workbook(self.path)
        sheet = book.sheet_by_name(self.sheetname)
        
        html = ""
        items = self.get_excel_items(sheet)
        
        for item in items:
            if item["abreviation"] != "":
                html += self.format_project_link(item)        

        book.unload_sheet(self.sheetname)    
        return html

    def format_project_link(self,item):

        thumb_image_url = "http://shared.runmc-radiology.nl/mediawiki/challenges/localImage.php?file="+item["abreviation"]+".png"
        external_thumb_html = "<img class='linkoverlay' src='/static/css/lg_exitdisclaimer.png' height='40' border='0' width='40'>" 
        
        overview_article_html = ""
        if item["overview article url"] != "":
            overview_article_html = '<br>Overview article: <a class="external free" href="%(url)s">%(url)s</a>' % ({"url" : item["overview article url"]})
            
        
        classes = []        
        section = item["website section"].lower()
        if section == "upcoming challenges":
            classes.append("upcoming")
        elif section == "active challenges":
            classes.append("active")
        elif section == "past challenges":
            classes.append("inactive")
        
    
        HTML = """
        <table class="%(classes)s">
            <tbody>
                <tr >
                    <td class="project_thumb">
                        <span class="plainlinks externallink" id="%(abreviation)s">
                            
                            
                            <a href="%(url)s">
                                <img alt="" src="%(thumb_image_url)s" height="100" border="0" width="100">
                                %(external_thumb_html)s
                                
                            </a>
                            
                            
                            
                        </span>
                    </td>
                    <td>
                        %(description)s<br>Website: <a class="external free" title="%(url)s" href="%(url)s">
                            %(url)s
                        </a>
                        <br>Event:
                        <a class="external text" title="%(event_name)s"
                            href="%(event_url)s">%(event_name)s
                        </a>
                        %(overview_article_html)s
                    </td>
                </tr>
            </tbody>
        </table>
        """ % ({"classes": "projectlink " + " ".join(classes), 
                "abreviation" : item["abreviation"],
                "url" : item["URL"],
                "thumb_image_url" : thumb_image_url,
                "external_thumb_html":external_thumb_html,
                "description" : item["description"],
                "event_name" : item["event name"],
                "event_url" : item["event URL"],
                "overview_article_html" : overview_article_html
               })

        return HTML


    def get_excel_items(self,sheet):
        """ Treat each row in excel sheet as an item. First row in sheet should
        contain column headers. Each item returned is an object that has a field
        for each column.
        
        """    
        items = []

        for row in range(1,sheet.nrows): #skip first row as those are titles        
            items.append(self.get_excel_item(sheet,row))
        return items
        
        
    def get_excel_item(self,sheet,row):
        """
        """
        item = {}
        
        col_titles = sheet.row_values(0,0)
        col_values = sheet.row_values(row,0)
        for (title,value) in zip(col_titles,col_values):
           
            if title != "":
                item[title] = value

        
        return item






    
