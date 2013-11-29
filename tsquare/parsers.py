from copy import deepcopy
import HTMLParser
import re

try:
    from BeautifulSoup import BeautifulSoup as soup
    BS_AVAILABLE = True
except ImportError:
    print "WARNING - BS4 NOT AVAILABLE"
    BS_AVAILABLE = False

class HTMLScraperInterface(object):
    def get_iframes(self, html_in):
        raise NotImplementedError('Subclasses of HTMLScraperInterface should override this method')

    def get_tools(self, html_in):
        raise NotImplementedError('Subclasses of HTMLScraperInterface should override this method')

    def get_assignments(self, html_in):
        raise NotImplementedError('Subclasses of HTMLScraperInterface should override this method')

    def get_grades(self, html_in):
        raise NotImplementedError('Subclasses of HTMLScraperInterface should override this method')

class LXMLParser(HTMLScraperInterface):
    
    def get_iframes(self, html_in):
        doc = soup(html_in)
        frame_attrs = dict(doc.iframe.attrs)
        return [{'name' : frame_attrs['name'],
                 'title': frame_attrs['title'],
                 'src'  : frame_attrs['src'] }]
            

    def get_tools(self, html_in):
        doc = soup(html_in)
        out_dict_list = []
        for tab in doc.findAll('a'):
            class_type = tab.get('class')
            if class_type and re.match('icon-sakai-*', class_type):
                    out_dict_list.append({'name': tab.get('class')[11:].strip(),
                                     'href': tab.get('href'),
                                     'desc': tab.get('title')})
        return out_dict_list
        
    def get_assignments(self, html_in):
        doc = soup(html_in)
        out_list = []
        table = doc.table
        for i, table_row in enumerate(table('tr')):
            if i == 0:
                # skip the table header row
                pass
            else:
                temp_obj = { 'href' : table_row.a['href'] }
                for table_col in table_row('td'):
                    header = table_col.get('headers')
                    if header is not None:
                        temp_obj[header] = table_col.text.strip()
                out_list.append(temp_obj)
        return out_list

    def get_grades(self, html_in):
        doc = soup(html_in)
        out_dict = {}
        tables = doc.findAll('table')
        # tables[0] is the header that we don't care about
        # tables[1] is the course grade
        course_grade_table = tables[1]
        if tables[1].span:
            out_dict['course_grade'] = { 'letter_grade': tables[1].span.text,
                                         'number_grade': tables[1]('span')[1].text }
        else:
            out_dict['course_grade'] = { 'error' : 'Not yet available'}
        out_dict['grades'] = {}
        # tables[2] is a bunch of javascript and all of the grade data.
        # first we have to strip away the javascript.
        row_data = [x for x in tables[2]('td')]
        _NEXT_FIELD = 'name'
        _CURRENT_CATEGORY = ''
        _temp = {}
        for row in row_data:
            if row.img:

                # this is the first row of the table
                continue
            if row.span:
                # this is a category
                _CURRENT_CATEGORY = row.span.text.strip()
                if not _CURRENT_CATEGORY in out_dict['grades']:
                    out_dict['grades'][_CURRENT_CATEGORY] = []
            elif row.get('class') == 'left' and _NEXT_FIELD == 'name':
                # this is a grade name
                _temp['name'] = row.text
                _NEXT_FIELD = 'date'
            elif _NEXT_FIELD == 'date':
                _temp['date'] = row.text
                _NEXT_FIELD = 'grade'
            elif _NEXT_FIELD == 'grade':

                _temp['grade'] = row.text
                _NEXT_FIELD = 'comments'
            elif _NEXT_FIELD == 'comments':
                _temp['comments'] = row.text
                _NEXT_FIELD = 'attachment'
            elif _NEXT_FIELD == 'attachment':
                # ignore this for now
                _NEXT_FIELD = 'name'
                if _CURRENT_CATEGORY == '':
                    if not 'unnamed' in out_dict['grades']:
                        out_dict['grades']['unnamed'] = []
                    out_dict['grades']['unnamed'].append(_temp)
                    _temp = {}
                else:
                    out_dict['grades'][_CURRENT_CATEGORY].append(_temp)
                    _temp = {}
        return out_dict

    def get_syllabus(self, html_in)
        soup_html = soup(html_in)
        table = soup_html('table')
        html = table.__repr__()[1:-1] # SERIOUSLY beautifulsoup????
        return html

class DefaultParser(HTMLScraperInterface):
    def get_iframes(self, html_in):
        return _IFrameParser().get_iframes(html_in)

    def get_tools(self, html_in):
        return _SiteToolHTMLParser().get_tools(html_in)

    def get_assignments(self, html_in):
        return _AssignmentHTMLParser().get_assignments(html_in)

        
class _IFrameParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._iframes = []

    def handle_starttag(self, tag, attrs):
        first_attr = dict(attrs)
        if tag == 'iframe':
            self._iframes.append({ 'name' : first_attr['name'],
                                   'title': first_attr['title'].strip(),
                                   'src'  : first_attr['src']})

    def get_iframes(self, html_input):
        self.feed(html_input)
        return self._iframes
    
    
class _SiteToolHTMLParser(HTMLParser.HTMLParser):
    
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._tools = []

    def handle_starttag(self, tag, attrs):
        first_attr = dict(attrs)
        # if this is a link with a class attribute
        if tag == 'a' and 'class' in first_attr:
            # look for tools
            if first_attr['class'].strip() == 'icon-sakai-syllabus':
                self._tools.append({ 'name': 'syllabus',
                                     'href': first_attr['href'],
                                     'desc': first_attr['title']})
            elif first_attr['class'].strip() == 'icon-sakai-resources':
                self._tools.append({ 'name': 'resources',
                                     'href': first_attr['href'],
                                     'desc': first_attr['title']})
            elif first_attr['class'].strip() == 'icon-sakai-assignment-grades':
                self._tools.append({ 'name': 'assignments',
                                     'href': first_attr['href'],
                                     'desc': first_attr['title']})
            elif first_attr['class'].strip() == 'icon-sakai-gradebook-tool':
                self._tools.append({ 'name': 'grades',
                                     'href': first_attr['href'],
                                     'desc': first_attr['title']})

    def get_tools(self, html_text):
        self.feed(html_text)
        return self._tools

    def purge(self):
        self._tools = []

class _AssignmentHTMLParser(HTMLParser.HTMLParser):

    _PARSER_STATE = ['WAITING_FOR_H4',
                     'WAITING_FOR_LINK'
                     'WAITING_FOR_STATUS',
                     'WAITING_FOR_OPEN_DATE',
                     'WAITING_FOR_DUE_DATE']

    _LEXER_STATE = ['STARTING_STATE',
                    'NEXT_IS_TITLE',
                    'NEXT_IS_STATUS',
                    'NEXT_IS_OPEN_DATE',
                    'NEXT_IS_DUE_DATE']

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._assignments = []
        self._state = 'WAITING_FOR_H4'
        self._lstate = 'STARTING_STATE'
        self._constructed_obj = {}

    def _assert_state(self, desired_state, desired_lstate):
        return self._state == desired_state and self._lstate == desired_lstate 

    def handle_starttag(self, tag, attr):
        first_attr = dict(attr)
        if tag == 'h4':
            # this is an assignment name
            if self._assert_state('WAITING_FOR_H4', 'STARTING_STATE'):
                self._state = 'WAITING_FOR_LINK'
        elif tag == 'a':
            # this is a link
            if self._assert_state('WAITING_FOR_LINK', 'STARTING_STATE'):
                self._constructed_obj['href'] = first_attr['href']
                self._state = 'WAITING_FOR_TITLE'
                self._lstate = 'NEXT_IS_TITLE'
        elif tag == 'td':
            # this is a table
            if 'headers' in first_attr:
                if first_attr['headers'] == 'status':
                    self._lstate = 'NEXT_IS_STATUS'
                elif first_attr['headers'] == 'openDate':
                    self._lstate = 'NEXT_IS_OPEN_DATE'
                elif first_attr['headers'] == 'dueDate':
                    self._lstate = 'NEXT_IS_DUE_DATE'

    def handle_data(self, data):
        stripped_data = data.strip('\t\n')
        if len(stripped_data) == 0:
            return
        if self._assert_state('WAITING_FOR_TITLE', 'NEXT_IS_TITLE'):
            self._constructed_obj['title'] = stripped_data
            self._state = 'WAITING_FOR_STATUS'
            self._lstate = 'STARTING_STATE'
        elif self._assert_state('WAITING_FOR_STATUS', 'NEXT_IS_STATUS'):
            self._constructed_obj['status'] = stripped_data
            self._state = 'WAITING_FOR_OPEN_DATE'
            self._lstate = 'STARTING_STATE'
        elif self._assert_state('WAITING_FOR_OPEN_DATE', 'NEXT_IS_OPEN_DATE'):
            self._constructed_obj['openDate'] = stripped_data
            self._state = 'WAITING_FOR_DUE_DATE'
            self._lstate = 'STARTING_STATE'
        elif self._assert_state('WAITING_FOR_DUE_DATE', 'NEXT_IS_DUE_DATE'):
            self._constructed_obj['dueDate'] = stripped_data
            self._assignments.append(deepcopy(self._constructed_obj))
            self._constructed_obj = {}
            self._state = self._PARSER_STATE[0]
            self._lstate = self._LEXER_STATE[0]

    def get_assignments(self, html_input):
        self.feed(html_input)
        return self._assignments

    def purge(self):
        self._assignments = []
        self._constructed_obj = {}
        self._state = self._PARSER_STATE[0]
        
REGISTERED_METHODS = { 'default' : DefaultParser,
                       'bs4'     : LXMLParser }