"""
Tests of noms.server, mostly handlers
"""
import json
import re
from cStringIO import StringIO

from twisted.web.test.requesthelper import DummyRequest
from twisted.python.components import registerAdapter
from twisted.internet import defer

import treq

from klein.app import KleinRequest, KleinResource
from klein.interfaces import IKleinRequest

import attr

from mock import patch, ANY

from pytest import fixture, inlineCallbacks

from noms import server, fromNoms, config, recipe, urlify, CONFIG
from noms.rendering import ResponseStatus as RS, OK, ERROR


# klein adapts Request to KleinRequest internally when the Klein() object
# begins handling a request. This isn't explicitly done for DummyRequest
# (because this is an object that only appears in tests), so we create our own
# adapter -- now we can use DummyRequest wherever a Klein() object appears in
# our code
registerAdapter(KleinRequest, DummyRequest, IKleinRequest)


def test_querySet(mockConfig):
    """
    Does querySet(fn)() render the result of the cursor returned by fn?
    """
    def _configs(req):
        return config.Config.objects()

    configsFn = server.querySet(_configs)
    assert configsFn(None) == '[{"apparentURL": "https://app.nomsbook.com"}]'


DEFAULT_HEADERS = (
    ('user-agent', ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0)']),
    ('cookie', ['']),
    )


def request(postpath, requestHeaders=DEFAULT_HEADERS, responseHeaders=(), **kwargs):
    """
    Build a fake request for tests
    """
    req = DummyRequest(postpath)
    for hdr, val in requestHeaders:
        req.requestHeaders.setRawHeaders(hdr, val)

    for hdr, val in responseHeaders:
        req.setHeader(hdr, val)

    for k, v in kwargs.items():
        if k.startswith('session_'):
            ses = req.getSession()
            setattr(ses, k[8:], v)
        else:
            setattr(req, k, v)

    return req


def requestJSON(postpath, requestHeaders=DEFAULT_HEADERS, responseHeaders=(), **kwargs):
    """
    As ServerTest.request, but force content-type header, and coerce
    kwargs['content'] to the right thing
    """
    content = kwargs.pop('content', None)
    if isinstance(content, dict):
        kwargs['content'] = StringIO(json.dumps(content))
    elif content: # pragma: nocover
        kwargs['content'] = StringIO(str(content))
    else:
        kwargs['content'] = None

    responseHeaders = responseHeaders + (('content-type', ['application/json']),)
    req = request(postpath, requestHeaders, responseHeaders, **kwargs)

    return req



@attr.s(init=False)
class EZServer(object):
    """
    Convenience abstraction over Server/APIServer to simplify test code
    """
    cls = attr.ib()
    inst = attr.ib(default=None)


    def __init__(self, cls):
        self.cls = cls
        self.inst = cls()

    def handler(self, handlerName, req=None, *a, **kw):
        """
        Convenience method, call a Server.app endpoint with a request
        """
        if req is None:
            # postpath is empty by default because we're directly executing the
            # endpoint, so there should be nothing left to consume in the url
            # path. In other words, we've already found the final resource when
            # execute_endpoint is called.
            postpath = kw.pop('postpath', [])
            req = request(postpath)

        return defer.maybeDeferred(
                self.inst.app.execute_endpoint,
                handlerName, req, *a, **kw
                )


@fixture
def rootServer():
    """
    Instance of EZServer using the server.Server routes
    """
    return EZServer(server.Server)


@fixture
def apiServer():
    """
    Instance of EZServer using the server.APIServer routes
    """
    return EZServer(server.APIServer)


@fixture
def req():
    """
    Basic empty request
    """
    return request([])


@fixture
def reqJS():
    """
    Basic empty request that uses JSON request wrapping/unwrapping
    """
    return requestJSON([])


@inlineCallbacks
def test_static(mockConfig, rootServer):
    """
    Does /static/ return a FilePath?
    """
    with fromNoms:
        r = yield rootServer.handler('static', postpath=['js', 'app.js'])
        assert 'app.js' in r.child('js').listdir()


@inlineCallbacks
def test_index(mockConfig, rootServer, req):
    """
    Does / return the home page?
    """
    r = yield rootServer.handler('index', req)
    assert re.search(r'<title>NOM NOM NOM</title>', r.render(req))


@inlineCallbacks
def test_showRecipes(mockConfig, rootServer, req):
    """
    Does /recipes list recipes?
    """
    r = yield rootServer.handler('showRecipes', req)
    assert re.search(r'partials/recipe-list.html', r.render(req))


@inlineCallbacks
def test_createRecipe(mockConfig, rootServer, req):
    """
    Does /recipes/new show the creation page?
    """
    r = yield rootServer.handler('createRecipe', req)
    assert re.search(r'partials/recipe-new.html', r.render(req))


@inlineCallbacks
def test_createIngredient(mockConfig, rootServer, req):
    """
    Does /ingredients/new show the ingredient creation page?
    """
    r = yield rootServer.handler('createIngredient', req)
    assert re.search(r'partials/ingredient-new.html', r.render(req))


@inlineCallbacks
def test_showRecipe(mockConfig, rootServer, req):
    """
    Does /recipes/xxx show recipe xxx?
    """
    r = yield rootServer.handler('showRecipe', req, 'foo-gmail-com-honeyed-cream-cheese-pear-pie-')
    rendered = r.render(req)
    assert re.search(r'partials/recipe.html', rendered)
    assert re.search(r'nomsPreload.*urlKey.*foo-gmail-com-honeyed-cream-cheese-pear-pie-',
        rendered)


@inlineCallbacks
def test_api(mockConfig, rootServer, req):
    """
    Does the /api/ URL hand off to the right resource?
    """
    # does it create the _api object when needed?
    assert rootServer.inst._api is None
    r1 = yield rootServer.handler('api', req)
    assert r1 is rootServer.inst._api
    assert isinstance(r1, KleinResource)

    # does it return the same _api object when requested again?
    r2 = yield rootServer.handler('api', req)
    assert r1 is r2


@fixture
def recipes():
    """
    Set up some recipes explicitly during a test
    """
    author = u'cory'
    url = urlify(u'weird sandwich', author)
    r1 = recipe.Recipe(name=u'weird sandwich', author=author, urlKey=url).save()
    url = urlify(u'weird soup', author)
    r2 = recipe.Recipe(name=u'weird soup', author=author, urlKey=url).save()
    return (r1, r2)


@inlineCallbacks
def test_getRecipe(mockConfig, apiServer, recipes, reqJS):
    """
    Does /api/recipe/.... return a specific recipe?
    """
    r = yield apiServer.handler('getRecipe', reqJS, 'weird-soup-cory-')
    assert r['name'] == 'weird soup'


@inlineCallbacks
def test_recipeList(mockConfig, apiServer, recipes):
    """
    Does /api/recipe/list return a structured list of recipes from the database?
    """
    r = json.loads((yield apiServer.handler('recipeList')))
    keys = [x['urlKey'] for x in r]
    assert keys == ['weird-sandwich-cory-', 'weird-soup-cory-']


@inlineCallbacks
def test_user(mockConfig, apiServer, weirdo):
    """
    Does /api/user return the current user?
    """
    req = requestJSON([], session_user=weirdo)
    r = yield apiServer.handler('user', req)
    assert r.email == 'weirdo@gmail.com'


@inlineCallbacks
def test_sso(mockConfig, apiServer, req, weirdo):
    """
    Does /api/sso create or return a good user?
    """
    pPost = patch.object(treq, 'post',
            return_value=defer.succeed(None),
            autospec=True)
    pGet = patch.object(treq, 'get',
            return_value=defer.succeed(None),
            autospec=True)

    @defer.inlineCallbacks
    def negotiateSSO(req=req, **user):
        def auth0tokenizer():
            return defer.succeed({'access_token': 'IDK!@#BBQ'})

        def auth0userGetter():
            return defer.succeed(dict(**user))

        pContent = patch.object(treq, 'json_content',
                side_effect=[auth0tokenizer(), auth0userGetter()],
                autospec=True)

        with pPost as mPost, pGet as mGet, pContent:
            yield apiServer.handler('sso', req)
            mPost.assert_called_once_with(
                server.TOKEN_URL,
                json.dumps({'client_id': 'abc123',
                 'client_secret': 'ABC!@#',
                 'redirect_uri': CONFIG.apparentURL + '/api/sso',
                 'code': 'idk123bbq',
                 'grant_type': 'authorization_code',
                 }, sort_keys=True),
                headers=ANY)
            mGet.assert_called_once_with(server.USER_URL + 'IDK!@#BBQ')

    # test once with an existing user
    reqJS = requestJSON([], args={'code': ['idk123bbq']})
    yield negotiateSSO(reqJS, email=weirdo.email)
    assert reqJS.getSession().user == weirdo
    assert reqJS.responseCode == 302
    assert reqJS.responseHeaders.getRawHeaders('location') == ['/']

    # test again with a new user
    reqJS = requestJSON([], args={'code': ['idk123bbq']})
    yield negotiateSSO(reqJS,
            email='weirdo2@gmail.com',
            family_name='2',
            given_name='weirdo'
            )
    assert reqJS.getSession().user.email == 'weirdo2@gmail.com'
    assert reqJS.responseCode == 302
    assert reqJS.responseHeaders.getRawHeaders('location') == ['/']


@inlineCallbacks
def test_noRecipeToBookmark(mockConfig, weirdo, apiServer):
    """
    Does the application still work if there are no recipes?
    """
    pageSource = ''
    pGet = patch.object(treq, 'get', return_value=defer.succeed(None), autospec=True)
    pTreqContent = patch.object(treq, 'content', return_value=defer.succeed(pageSource), autospec=True)

    with pGet, pTreqContent:
        reqJS = requestJSON([], session_user=weirdo)
        reqJS.args['uri'] = ['http://www.foodandwine.com/recipes/poutine-style-twice-baked-potatoes']
        ret = yield apiServer.handler('bookmarklet', reqJS)
        expectedResults = server.ClipResponse(
                status=RS.error, message=server.ResponseMsg.noRecipe,
                recipes=[],
                )
        assert ret == expectedResults


@inlineCallbacks
def test_bookmarklet(mockConfig, apiServer, anonymous, weirdo, recipePageHTML):
    """
    Does api/bookmarklet fetch, save, and return a response for the recipe?
    """
    pGet = patch.object(treq, 'get', return_value=defer.succeed(None), autospec=True)
    pTreqContent = patch.object(treq, 'content', return_value=defer.succeed(recipePageHTML), autospec=True)

    with pGet, pTreqContent:
        # normal bookmarkleting
        reqJS = requestJSON([], session_user=weirdo)
        reqJS.args['uri'] = ['http://www.foodandwine.com/recipes/poutine-style-twice-baked-potatoes']
        ret = yield apiServer.handler('bookmarklet', reqJS)
        assert len(recipe.Recipe.objects()) == 1
        expectedResults = server.ClipResponse(
                status=RS.ok, message='',
                recipes=[{"name": "Delicious Meatless Meatballs", "urlKey": "weirdo-gmail-com-delicious-meatless-meatballs-"}]
                )
        assert ret == expectedResults

        # not signed in to noms; bookmarkleting should not be allowed
        reqJS = requestJSON([])
        reqJS.args['uri'] = ['http://www.foodandwine.com/recipes/poutine-style-twice-baked-potatoes']
        ret = yield apiServer.handler('bookmarklet', reqJS)
        expectedResults = server.ClipResponse(
                status=RS.error, message=server.ResponseMsg.notLoggedIn,
                recipes=[],
                )
        assert ret == expectedResults


@fixture
def weirdSoupPOST():
    """
    Data structure for a recipe posted from the create form
    """
    return dict(
            name='Weird soup',
            author='Weird Soup Man',
            ingredients=['weirdness', 'soup'],
            instructions=['mix together ingredients', 'heat through'],
            )


@inlineCallbacks
def test_createRecipeSave(mockConfig, apiServer, weirdo, weirdSoupPOST):
    """
    Do we save data from the create form successfully?
    """
    reqJS = requestJSON([], content=weirdSoupPOST, session_user=weirdo)
    resp = yield apiServer.handler('createRecipeSave', reqJS)
    assert resp == OK()

    # the second time we should get an error because it exists
    reqJS = requestJSON([], content=weirdSoupPOST, session_user=weirdo)
    resp = yield apiServer.handler('createRecipeSave', reqJS)
    assert resp == ERROR(message=server.ResponseMsg.renameRecipe)

    anonJS = requestJSON([])
    resp = yield apiServer.handler('createRecipeSave', anonJS)
    assert resp == ERROR(message=server.ResponseMsg.notLoggedIn)