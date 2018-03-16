from pathlib import Path

from dataproviders.ProjectExcelReader import ProjectExcelReader


def test_project_excel_reader():
    reader = ProjectExcelReader(
        Path(__file__).parent / 'resources' / 'challengestats.xls',
        'Challenges'
    )

    project_links = reader.get_project_links()

    assert len(project_links) == 134

    projectlink = project_links[0]

    assert projectlink.params["year"] == 2018
    assert projectlink.params["abreviation"] == 'dsb18'
    assert projectlink.params[
               "URL"] == 'https://www.kaggle.com/c/data-science-bowl-2018'
    assert projectlink.params["title"] == 'Data Science Bowl 2018'
    assert projectlink.params["description"]

    for projectlink in project_links:
        assert isinstance(projectlink.params['year'], int)
        assert isinstance(projectlink.params['abreviation'], str)
        assert isinstance(projectlink.params['URL'], str)
        assert isinstance(projectlink.params['title'], str)
        assert isinstance(projectlink.params['description'], str)
