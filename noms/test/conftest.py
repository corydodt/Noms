"""
Fixtures and common options for pytest tests
"""
from pytest import fixture

from mongoengine import connect, Document

from codado import fromdir

from noms import DBAlias, DBHost
from noms import documentutil


_client = None


@fixture(scope='session', autouse=True)
def useTheTestDatabase():
    """
    When starting to test, connect to the test database, making it the default
    connection, and pre-empting other code that connects to the database.
    """
    global _client
    if _client is None:
        _client = connect(**DBHost[DBAlias.nomsTest])


class _MongoEngineHack(Document):
    """
    Document class solely for the purpose of getting access to the db object.

    This is the easiest way to find the db, since get_default_database is
    broken.
    """


@fixture
def mockDatabase():
    """
    Mongomock-based interface to a "database"
    """
    try:
        db = _MongoEngineHack._get_db()
        _scrubMongoEngineBecauseMongoEngineIsSoStupid(_client, db)
        yield db
    finally:
        _scrubMongoEngineBecauseMongoEngineIsSoStupid(_client, db)


def assertFailure(deferred, *expectedFailures):
    """
    Fail if C{deferred} does not errback with one of C{expectedFailures}.
    Returns the original Deferred with callbacks added. You will need
    to return this Deferred from your test case.

    *COPIED SHAMELESSLY FROM twisted.trial._asynctest.TestCase*
    """
    def _cb(ignore):
        raise AssertionError(
            "did not catch an error, instead got %r" % (ignore,))

    def _eb(failure):
        if failure.check(*expectedFailures):
            return failure.value
        else:
            output = ('\nExpected: %r\nGot:\n%s'
                      % (expectedFailures, str(failure)))
            raise AssertionError(output)
    return deferred.addCallbacks(_cb, _eb)


def onSave(doc):
    """
    Hook into Document.save() and keep a reference to any object in our
    application that was saved. We can later call unsave() to remove them.
    """
    _unsaves.add(doc)


_unsaves = set()

documentutil.onSave = onSave


def unsave():
    """
    Remove all Document instances which were previously saved by tests
    """
    for x in _unsaves:
        x.delete()

    _unsaves.clear()


def _scrubMongoEngineBecauseMongoEngineIsSoStupid(client, db):
    """
    XXX - Mongoengine and mongomock do NOT work well together. Collection switching
    and other factors mean you have to scrub every collection, every time.
    Dropping the database doesn't work.
    """
    unsave()
    client.drop_database(db)


@fixture
def mockConfig(mockDatabase):
    """
    Define database connections for code that needs mongo
    """
    # in tests, we replace the global CONFIG without patching it
    from noms import CONFIG
    assert '_realConfig' not in CONFIG.__dict__

    try:
        cols = mockDatabase.collection_names()
        docs = sum(mockDatabase[c].count() for c in cols)
        assert docs == 0

        from noms.config import Config
        cfg = Config(cliOptions={'alias': DBAlias.nomsTest})
        cfg.save()

        from noms import secret
        secret.put('auth0', 'abc123', 'ABC!@#')
        secret.put('localapi', 'localapi', '!@#ABC')

        CONFIG.load()
        yield CONFIG

    finally:
        # despite dropping the database we have to do this, because it's
        # still an object in memory
        cfg.delete()

    if '_realConfig' in CONFIG.__dict__:
        del CONFIG.__dict__['_realConfig']


@fixture
def specialUsers():
    """
    Preload the special users
    """
    from noms import user
    user.USER()


@fixture
def weirdo(mockConfig):
    """
    Preload the weirdo user

    The mockConfig fixture here is required so that the User object has a
    collection pointing to the mock database, otherwise it wouldn't be
    possible to save it in the mock database.
    """
    from noms import user
    return user.User(
            email='weirdo@gmail.com', 
            givenName='Weirdo',
            familyName='User', 
            roles=[user.Roles.user]).save()


@fixture
def recipePageHTML():
    return open(fromdir(__file__)('recipe_page_source.html')).read()

