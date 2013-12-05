import requests
import parsers

BASE_URL_GATECH = 'https://login.gatech.edu/cas/'
SERVICE = 'https://t-square.gatech.edu/sakai-login-tool/container'
BASE_URL_TSQUARE = 'https://t-square.gatech.edu/direct/'

class TSquareException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class TSquareAuthException(TSquareException):
    pass

class NotAuthenticatedException(TSquareException):
    pass


class SessionExpiredException(TSquareException):
    pass


class AssignmentParseException(TSquareException):
    pass


class TSquareAPI(object):
    def requires_authentication(func):
        """
        Function decorator that throws an exception if the user
        is not authenticated, and executes the function normally
        if the user is authenticated.
        """
        def _auth(self, *args, **kwargs):
            if not self._authenticated:
                raise NotAuthenticatedException('Function {} requires'
                                                .format(func.__name__)
                                                + ' authentication')
            else:
                return func(self, *args, **kwargs)
        return _auth

    def __init__(self, username, password,
                 scraper='bs4'):
        """
        Initialize a TSquareAPI object.
        Logs in to TSquare with username and password.
        @param username - The username to log in with
        @param password - The password to log in with. Not stored.

        @returns A TSquareUser object that represents the user that
                 was logged in.
        @throws TSquareAuthException - If something goes wrong during the
        authentication process (i.e. credentials are bad)
        """
        self._authenticated = True
        self.username = username
        self._tg_ticket, self._service_ticket = _get_ticket(username, password)
        self._session = _tsquare_login(self._service_ticket)
        try:
            self._html_iface = parsers.REGISTERED_METHODS[scraper]()
        except KeyError:
            self._html_iface = parsers.REGISTERED_METHODS['default']()
        

    @requires_authentication
    def logout(self):
        self._session.delete(BASE_URL_GATECH + 'rest/tickets/{}'.format(self._tg_ticket))
        self._authenticated = False
        
    @requires_authentication
    def get_user_info(self):
        """
        Returns a TSquareUser object representing the currently logged in user.
        Throws a NotAuthenticatedException if the user is not authenticated.
        """
        response = self._session.get(BASE_URL_TSQUARE + '/user/current.json')
        response.raise_for_status() # raises an exception if not 200: OK
        user_data = response.json()
        del user_data['password'] # tsquare doesn't store passwords
        return TSquareUser(**user_data)

    @requires_authentication
    def get_site_by_id(self, id):
        """
        Looks up a site by ID and returns a TSquareSite representing that
        object, or throws an exception if no such site is found.
        @param id - The entityID of the site to look up
        @returns A TSquareSite object
        """
        response = self._session.get(BASE_URL_TSQUARE + '/site/{}.json'.format(id))
        response.raise_for_status()
        site_data = response.json()
        return TSquareSite(**site_data)
        
    @requires_authentication
    def get_sites(self, filter_func=lambda x: True):
        """
        Returns a list of TSquareSite objects that represent the sites available
        to a user.
        @param filter_func - A function taking in a Site object as a parameter
                             that returns a True or False, depending on whether
                             or not that site should be returned by this
                             function. Filter_func should be used to create
                             filters on the list of sites (i.e. user's
                             preferences on what sites to display by default).
                             If not specified, no filter is applied.
        @returns - A list of TSquareSite objects encapsulating t-square's JSON
                   response.
        """
        response = self._session.get(BASE_URL_TSQUARE + 'site.json')
        response.raise_for_status() # raise an exception if not 200: OK
        site_list = response.json()['site_collection']
        if not site_list:
            # this means that this t-square session expired. It's up
            # to the user to re-authenticate.
            self._authenticated = False
            raise SessionExpiredException('The session has expired')
        result_list = []
        for site in site_list:
            t_site = TSquareSite(**site)
            if not hasattr(t_site, "props"):
                t_site.props = {}
            if not 'banner-crn' in t_site.props:
                t_site.props['banner-crn'] = None
            if not 'term' in t_site.props:
                t_site.props['term'] = None
            if not 'term_eid' in t_site.props:
                t_site.props['term_eid'] = None
            if filter_func(t_site):
                result_list.append(t_site)
        return result_list
            
    @requires_authentication
    def get_announcements(self, site=None, num=10, age=20):
        """
        Gets announcements from a site if site is not None, or from every
        site otherwise. Returns a list of TSquareAnnouncement objects.
        @param site_obj (TSquareSite) If non-None, gets only the announcements
                                      from that site. If none, get anouncements
                                      from all sites.
        @param num - The number of announcements to fetch. Default is 10.
        @param age - 'How far back' to go to retreive announcements. Default
                     is 20, which means that only announcements that are
                     less than 20 days old will be returned, even if there
                     less than 'num' of them.
        @returns - A list of TSquareAnnouncement objects. The length will be
                   at most num, and it may be less than num depending on
                   the number of announcements whose age is less than age.
        """
        url = BASE_URL_TSQUARE + 'announcement/'
        if site:
            url += 'site/{}.json?n={}&d={}'.format(site.id, num, age)
        else:
            url += 'user.json?n={}&d={}'.format(num, age)
        request = self._session.get(url)
        request.raise_for_status()
        announcement_list = request.json()['announcement_collection']
        return map(lambda x: TSquareAnnouncement(**x), announcement_list)

    @requires_authentication
    def get_tools(self, site):
        """
        Gets all tools associated with a site.
        @param site (TSquareSite) - The site to search for tools
        @returns A list of dictionaries representing Tsquare tools.
        """
        # hack - gotta bypass the tsquare REST api because it kinda sucks with tools
        url = site.entityURL.replace('direct', 'portal')
        response = self._session.get(url)
        response.raise_for_status()
        # scrape the resulting html
        tools_dict_list = self._html_iface.get_tools(response.text)
        return [TSquareTool(**x) for x in tools_dict_list]

    @requires_authentication
    def get_assignments(self, site):
        """
        Gets a list of assignments associated with a site (class). Returns
        a list of TSquareAssignment objects.
        @param site (TSquareSite) - The site to use with the assignment query

        @returns - A list of TSquareSite objects. May be an empty list if
                   the site has defined no assignments.
        """
        tools = self.get_tools(site)
        assignment_tool_filter = [x.href for x in tools if x.name == 'assignment-grades']
        if not assignment_tool_filter:
            return []
        assignment_tool_url = assignment_tool_filter[0].href
        response = self._session.get(assignment_tool_url)
        response.raise_for_status()
        iframes = self._html_iface.get_iframes(response.text)
        iframe_url = ''
        for frame in iframes:
            if frame['title'] == 'Assignments ':
                iframe_url = frame['src']
        if iframe_url == '':
            print "WARNING: NO ASSIGNMENT IFRAMES FOUND"
        response = self._session.get(iframe_url)
        response.raise_for_status()
        assignment_dict_list = self._html_iface.get_assignments(response.text)
        return [TSquareAssignment(**x) for x in assignment_dict_list]

    @requires_authentication
    def get_grades(self, site):
        """
        Gets a list of grades associated with a site. The return type is a dictionary
        whose keys are assignment categories, similar to how the page is laid out
        in TSquare.
        """
        tools = self.get_tools(site)
        grade_tool_filter = [x.href for x in tools if x.name == 'gradebook-tool']
        if not grade_tool_filter:
            return []
        response = self._session.get(grade_tool_filter[0])
        response.raise_for_status()
        iframes = self._html_iface.get_iframes(response.text)
        iframe_url = ''
        for frame in iframes:
            if frame['title'] == 'Gradebook ':
                iframe_url = frame['src']
        if iframe_url == '':
            print "WARNING: NO GRADEBOOK IFRAMES FOUND"
        response = self._session.get(iframe_url)
        response.raise_for_status()
        grade_dict_list = self._html_iface.get_grades(response.text)
        return grade_dict_list

    @requires_authentication
    def get_syllabus(self, site):
        """
        Gets the syllabus for a course. The syllabus may or may not
        contain HTML, depending on the site. TSquare does not enforce
        whether or not pages are allowed to have HTML, so it is impossible
        to tell.
        """
        tools = self.get_tools(site)
        syllabus_filter = [x.href for x in tools if x.name == 'syllabus']
        if not syllabus_filter:
            return ''
        response = self._session.get(syllabus_filter[0])
        response.raise_for_status()
        iframes = self._html_iface.get_iframes(response.text)
        iframe_url = ''
        for frame in iframes:
            if frame['title'] == 'Syllabus ':
                iframe_url = frame['src']
        if iframe_url == '':
            print "WARHING: NO SYLLABUS IFRAME FOUND"
        response = self._session.get(iframe_url)
        response.raise_for_status()
        syllabus_html = self._html_iface.get_syllabus(response.text)
        return syllabus_html


class TSquareUser:
    def __init__(self, **kwargs):
        """
        Encapsulates the raw JSON dictionary that represents a user in TSquare.
        Converts a dictionary to attributes of an object for ease of use.
        This constructor should never be called directly; instead, it is
        called by get_user_info.
        """
        for key in kwargs:
            setattr(self, key, kwargs[key])

        def list_attrs(self):
            return self.__dict__.keys()

class TSquareSite:
    def __init__(self, **kwargs):
        """
        Encapsulates the raw JSON dictionary that represents a site in TSquare.
        Converts a dictionary to attributes of an object for ease of use.
        This constructor should never be called directly; instead, it is called
        by get_sites.
        """
        for key in kwargs:
            setattr(self, key, kwargs[key])

class TSquareAnnouncement:
    def __init__(self, **kwargs):
        """
        Encapsulates the raw JSON dictionary that represents an announcement
        in TSquare.
        Converts a dictionary to attributes of an object for ease of use.
        This constructor should never be called directly; instead, it is called
        by get_announcements.
        """
        for key in kwargs:
            setattr(self, key, kwargs[key])

class TSquareTool:
    def __init__(self, **kwargs):
        """
        Encapsulates the raw JSON dictionary that represents a tool in TSquare.
        A tool is any third party application that TSquare uses to provide a
        service. In this case, assignments, grades, and resources are the most
        common tools in use.
        """
        for key in kwargs:
            setattr(self, key, kwargs[key])

class TSquareAssignment:
    def __init__(self, **kwargs):
        """
        Encapsulates the dictionary that this module builds by scraping the
        Assignments page. An assignment is anything that can be turned
        in according to TSquare.
        """
        for key in kwargs:
            setattr(self, key, kwargs[key])
        
def _get_ticket(username, password):
    # step 1 - get a CAS ticket
    data = { 'username' : username, 'password' : password }
    response = requests.post(BASE_URL_GATECH + 'rest/tickets', data=data)
    if response.status_code == 400:
        raise TSquareAuthException('Username or password incorrect')
    elif not response.status_code == 201:
        raise TSquareAuthException('Received unexpected HTTP code: {}'
                                   .format(response.status_code))
    # black magic to strip the ticket out of the raw html response
    form_split = response.text.split('<form action="')[1].split(' ')[0]
    ticket = form_split.split('tickets/')[1][:-1]
    # step 2 - get a TSquare service ticket
    data = { 'service' : SERVICE }
    response = requests.post(BASE_URL_GATECH + 'rest/tickets/{}'.format(ticket),
                             data=data)
    if response.status_code == 400:
        raise TSquareAuthException('Parameters missing from ST call')
    elif not response.status_code == 200:
        raise TSquareAuthException('Received unexpected HTTP code: {}'
                                   .format(response.status_code))
    service_ticket = response.text
    return ticket, service_ticket


def _tsquare_login(service_ticket):
    session = requests.Session()
    # step 3 - redeem the ticket with TSquare and receive authenticated session
    session.get(SERVICE + '?ticket={}'.format(service_ticket))
    return session


