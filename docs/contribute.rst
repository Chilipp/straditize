.. _how-to-contribute:

Contributing, asking for assistance and reporting bugs
======================================================

First off, thanks for taking the time to contribute!

The following set of guidelines for contributing to straditize are
mostly guidelines, not rules. Use your best judgment, and feel free to
propose changes to this document in a pull request.

.. contents:: Table of Contents

Code of Conduct
---------------

This project and everyone participating in it is governed by the
`straditize Code of Conduct`_. By participating,
you are expected to uphold this code.

.. _straditize Code of Conduct: https://github.com/Chilipp/straditize/blob/master/CODE_OF_CONDUCT.md

How Can I Contribute?
---------------------

Reporting Bugs
~~~~~~~~~~~~~~

This section guides you through submitting a bug report for straditize.
Following these guidelines helps maintainers and the community
understand your report, reproduce the behavior, and find related
reports.

Before creating bug reports, please check existing issues and pull
requests as you might find out that you don't need to create one. When
you are creating a bug report, please `include as many details as
possible <#how-do-i-submit-a-good-bug-report>`__. Fill out `the required
template <https://github.com/Chilipp/straditize/blob/master/.github/issue_template.md>`__,
the information it asks for helps us resolve issues faster.

    **Note:** If you find a **Closed** issue that seems like it is the
    same thing that you're experiencing, open a new issue and include a
    link to the original issue in the body of your new one.

How Do I Submit A (Good) Bug Report?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bugs are tracked as `GitHub
issues <https://guides.github.com/features/issues/>`__. Create an issue
on straditize repository and provide the following information by
filling in `the template <https://github.com/Chilipp/straditize/blob/master/.github/issue_template.md>`__.

Explain the problem and include additional details to help maintainers
reproduce the problem:

-  **Use a clear and descriptive title** for the issue to identify the
   problem.
-  **Describe the exact steps which reproduce the problem** in as many
   details as possible.
-  **Provide specific examples to demonstrate the steps**. Include links
   to files or images, or copy/pasteable snippets, which you use in
   those examples. If you're providing snippets in the issue, use
   `Markdown code
   blocks <https://help.github.com/articles/markdown-basics/#multiple-lines>`__.
-  **Upload the project file**. The best is, you you only take the part
   of the stratigraphic diagram that causes the problems.
-  **Describe the behavior you observed after following the steps** and
   point out what exactly is the problem with that behavior.
-  **Explain which behavior you expected to see instead and why.**
-  **Include screenshots and animated GIFs** which show you following
   the described steps and clearly demonstrate the problem. You can use
   `this tool <https://www.cockos.com/licecap/>`__ to record GIFs on
   macOS and Windows, and `this
   tool <https://github.com/colinkeenan/silentcast>`__ or `this
   tool <https://github.com/GNOME/byzanz>`__ on Linux.
-  **If the problem is related to your data structure**, include a small
   example how a similar data structure can be generated

Include details about your configuration and environment:

-  **Which version of straditize and psyplot are you using?** You can
   get the exact version by running ``straditize -V`` and
   ``psyplot -aV`` in your terminal , or by starting the psyplot-gui and
   open Help->Dependencies.
-  **What's the name and version of the OS you're using**?
-  **Use conda's diagnostics!** If you installed straditize through
   anaconda, include the output of ``conda info -a`` and ``conda list``
   in your description

Suggesting Enhancements
~~~~~~~~~~~~~~~~~~~~~~~

If you want to change an existing feature, use the `change feature
template <https://github.com/Chilipp/straditize/issues/new?template=change_feature.md&title=CHANGE+FEATURE:>`__,
otherwise fill in the `new feature
template <https://github.com/Chilipp/straditize/issues/new?template=new_feature.md&title=NEW+FEATURE:>`__.

How Do I Submit A (Good) Enhancement Suggestion?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enhancement suggestions are tracked as `GitHub
issues <https://guides.github.com/features/issues/>`__. Create an issue
in the `straditize
repository <https://github.com/Chilipp/straditize/issues>`__ and follow
these steps:

-  **Use a clear and descriptive title** for the issue to identify the
   suggestion.
-  **Provide a step-by-step description of the suggested enhancement**
   in as many details as possible.
-  **Provide specific examples to demonstrate the steps**. Include
   copy/pasteable snippets which you use in those examples, as `Markdown
   code
   blocks <https://help.github.com/articles/markdown-basics/#multiple-lines>`__.
-  **Describe the current behavior** and **explain which behavior you
   expected to see instead** and why.
-  **Include screenshots and animated GIFs** which help you demonstrate
   the steps or point out the part of psyplot which the suggestion is
   related to. You can use `this
   tool <https://www.cockos.com/licecap/>`__ to record GIFs on macOS and
   Windows, and `this
   tool <https://github.com/colinkeenan/silentcast>`__ or `this
   tool <https://github.com/GNOME/byzanz>`__ on Linux.
-  **Explain why this enhancement would be useful** to most straditize
   users.
-  **List some other analysis software or applications where this
   enhancement exists.**
-  **Which version of straditize and psyplot are you using?** You can
   get the exact version by running ``straditize -V`` and
   ``psyplot -aV`` in your terminal , or by starting the psyplot-gui and
   open Help->Dependencies.
-  **Specify the name and version of the OS you're using.**

Pull Requests
~~~~~~~~~~~~~

-  Fill in `the required template <https://github.com/Chilipp/straditize/blob/master/.github/pull_request_template.md>`__
-  Do not include issue numbers in the PR title
-  Include screenshots and animated GIFs in your pull request whenever
   possible.
-  Document new code based on the `Documentation
   Styleguide <#documentation-styleguide>`__
-  End all files with a newline and follow the
   `PEP8 <https://www.python.org/dev/peps/pep-0008/>`__, e.g. by using
   `flake8 <https://pypi.org/project/flake8/>`__

Adding new examples
~~~~~~~~~~~~~~~~~~~

You have new examples? Great! straditize can only be improved through
new tutorials. You can either implement it in the graphical user
interface (see the
`straditize.widgets.tutorial <https://github.com/Chilipp/straditize/tree/master/straditize/widgets/tutorial>`__
module) or you just add them to the sphinx documentation. We are also
looking forward to assist you in the implementation and the sharing of
your experiences.

Styleguides
-----------

Git Commit Messages
~~~~~~~~~~~~~~~~~~~

-  Use the present tense ("Add feature" not "Added feature")
-  Use the imperative mood ("Move cursor to..." not "Moves cursor
   to...")
-  Limit the first line (summary) to 72 characters or less
-  Reference issues and pull requests liberally after the first line
-  When only changing documentation, include ``[ci skip]`` in the commit
   title

Documentation Styleguide
~~~~~~~~~~~~~~~~~~~~~~~~

-  Follow the `numpy documentation
   guidelines <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`__.
-  Use
   `reStructuredText <http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`__.
-  Try to not repeat yourself and make use of the
   ``straditize.common.docstrings``

Example
^^^^^^^

.. code:: python

    @docstrings.get_sectionsf('new_function')
    def new_function(a=1):
        """Make some cool new feature

        This function implements a cool new feature

        Parameters
        ----------
        a: int
            First parameter

        Returns
        -------
        something awesome
            The result"""
        ...

    @docstrings.dedent
    def another_new_function(a=1, b=2):
        """Make another cool new feature

        Parameters
        ----------
        %(new_function.parameters)s
        b: int
            Another parameter

        Returns
        -------
        Something even more awesome"""
        ...

    **Note:** This document has been inspired by `the contribution
    guidelines of
    Atom <https://github.com/atom/atom/blob/master/CONTRIBUTING.md#git-commit-messages>`__
