"""
Noms Python library - web application
"""
import re, inspect, types

DATABASE_NAME = "noms"

def urlify(*args):
    """
    Return a url-friendly version of name
    """
    args = list(args)

    for n in args: 
        assert isinstance(n, unicode), "Arguments pass to urlify must be unicode"

    url = args.pop(0)
    for n in args: 
        url = url + "-" + n
    url = url.encode('punycode')

    return re.sub(r'[^-a-z0-9]', '-', url.lower()) 


def eachMethod(decorator, methodFilter=lambda fName: True):
    """
    Class decorator that wraps every single method in its own method decorator

    methodFilter: a function which accepts a function name and should return 
    True if the method is one which we want to decorate, False if we want to
    leave this method alone.

    methodFilter can also be simply a string prefix. If it is a string, it is
    assumed to be the prefix we're looking for.
    """
    raise NotImplementedError("We can't figure out how to use this! :(")
    
    if isinstance(methodFilter, basestring):
        # Is it a string? If it is, change it into a function that takes a string.
        prefix = methodFilter
        methodFilter = lambda fName: fName.startswith(prefix)

    def innerDeco(cls):
        for fName, fn in inspect.getmembers(cls):
            if type(fn) is types.UnboundMethodType and methodFilter(fName):
                setattr(cls, fName, decorator(fn))
                
        return cls
    return innerDeco