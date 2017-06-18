How to Contribute to Noms 
=========================
Since we are an open source application, we love contributions however there are certain guideline to help us maintain our code quality. These guidelines are what we call "Definition of Done". 

Definition of Done 
------------------
Definition of Done for a noms case: 

- There should be 100% test coverage for both python and javascript.
- All automated test pass.
- Case has been code reviewed and approved by another developer.
- Appropriate documentation is written for the case.

Definition of Done for a noms release: 

- The release has been tagged for version control.
- Travis passes for the release tag.
- It deploys successfully using the continuous deployment system. 

Testing
-------
We currently use ``pytest`` as a tool to run test, but use with ``pytest`` and ``pyUnit/trial`` style for writing tests.

To run test on your local machine, use ``pytest``. To see whether or not your test passes on the CI server, you can go to ``github`` and view ``travis``. ``pytest`` is a tool to run tests, it also have a style of writing test. There are a few different ways to use pytest: 

- To run a specific test, use: ``pytest noms/test/test_rendering.py``
- To run all of the test, use: ``pytest``
- To run only the failing test, use: ``pytest --lf``

We change from ``trial`` to ``pytest`` because ``pytest`` and ``trial`` are both compatible with ``twisted``. ``pytest`` can be integrated with ``pyflakes`` and is faster than ``trial``.