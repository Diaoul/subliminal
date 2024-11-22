# Contributing

Thank you for considering contributing to *subliminal*!

This document presents general guidelines to make contributions easier.

## Translations

Contribution to translations can be made on [subliminal's transifex page](https://www.transifex.com/subliminal/subliminal/)
Subliminal is configured to work with [transifex-client](https://docs.transifex.com/client/)

## Issues

Issues are intended for bug report and feature requests.
For any bug report please make sure to include the complete stack trace and DEBUG level logs as well as reproduce steps.

If you use the CLI, you can create a debug log file with
`subliminal --debug [...] 2> debug.log`.

## Pull Requests

You can contribute code and documentation with pull requests.
Here follow some general guidelines for making a pull request.

### Workflow

- Any contribution is appreciated!
- Try to limit each pull request to *one* change only.
- Pull request should be linked to an issue. Create an issue first,
that is solved by this pull request.
- *Always* add tests and docs for your code.
  If tests are not passing, ask for advice.
- Make sure your changes pass our [CI].
  You won't get any feedback until it's green unless you ask for it.
- For the CI to pass, the coverage must be 100%.
  If you have problems to test something, open anyway and ask for advice.
  In some situations, we may agree to add an `# pragma: no cover`.
- Once you've addressed review feedback, make sure to bump the pull request with a short note, so we know you're done.
- Don’t break backwards-compatibility.


### Local Development Environment

You can (and should) run our test suite using [*tox*].
However, you’ll probably want a more traditional environment as well.

First, create a [virtual environment](https://virtualenv.pypa.io/) so you don't break your system-wide Python installation.
We recommend using the Python version from the `.python-version-default` file in project's root directory.

---

Then, [fork](https://github.com/Diaoul/subliminal/fork) the repository on GitHub.

Clone the fork to your computer:

```console
$ git clone git@github.com:<your-username>/subliminal.git
```

Or if you prefer to use Git via HTTPS:

```console
$ git clone https://github.com/<your-username>/subliminal.git
```

Then add the *subliminal* repository as *upstream* remote:

```console
$ git remote add -t main -m main --tags upstream https://github.com/Diaoul/subliminal.git
```

The next step is to sync your local copy with the upstream repository:

```console
$ git fetch upstream
```

This is important to obtain eventually missing tags, which are needed to install the development version later on.

Change into the newly created directory and after activating a virtual environment install an editable version of *subliminal* along with its tests and docs requirements:

```console
$ cd subliminal
$ python -m pip install --upgrade pip wheel  # PLEASE don't skip this step
$ python -m pip install -e '.[docs,types,tests,dev]'  # you can omit `docs` if you are not planning to build docs
```

At this point,

```console
$ python -m pytest
```

should work and pass.
You can *significantly* speed up the test suite by installing [*pytest-xdist*](https://github.com/pytest-dev/pytest-xdist)
and passing `-n auto` to *pytest* to take advantage of all your CPU cores.


To build the documentation and run doctests, use:

```console
$ tox run -e docs
```

You will find the built documentation in `docs/_build/html`.


---

To file a pull request, create a new branch on top of the upstream repository's `main` branch:

```console
$ git fetch upstream
$ git checkout -b my_topical_branch upstream/main
```

Make your changes, push them to your fork (the remote *origin*):

```console
$ git push -u origin
```

and publish the PR in GitHub's web interface!

After your pull request is merged and the branch is no longer needed, delete it:

```console
$ git checkout main
$ git push --delete origin my_topical_branch && git branch -D my_topical_branch
```

Before starting to work on your next pull request, run the following command to sync your local repository with the remote *upstream*:

```console
$ git fetch upstream -u main:main
```

---

To avoid committing code that violates our style guide, we strongly advise you to install [*pre-commit*] and its hooks:

```console
$ pre-commit install
```

This is not strictly necessary, because our [*tox*] file contains an environment that runs:

```console
$ pre-commit run --all-files
```

and our CI has integration with [pre-commit.ci](https://pre-commit.ci).
But it's way more comfortable to run it locally and *git* catching avoidable errors.


### Changelog

If your change is noteworthy, there needs to be a changelog entry so our users can learn about it!

To avoid merge conflicts, we use the [*Towncrier*](https://pypi.org/project/towncrier) package to manage our changelog.
*towncrier* uses independent *Markdown* files for each pull request – so called *news fragments* – instead of one monolithic changelog file.
On release, those news fragments are compiled into our [`HISTORY.rst`](https://github.com/Diaoul/subliminal/blob/main/HISTORY.rst).

You don't need to install *Towncrier* yourself, you just have to abide by a few simple rules:

- For each pull request, add a new file into `changelog.d` with a filename adhering to the `issue#.(breaking|change|provider|refiner|deprecation|misc).md` schema:
  For example, `changelog.d/42.change.md` for a non-breaking change that is proposed in issue #42.
- As with other docs, please use [semantic newlines] within news fragments.
- Wrap symbols like modules, functions, or classes into backticks so they are rendered in a `monospace font`.
- Wrap arguments into asterisks like in docstrings:
  `Added new argument *an_argument*.`
- If you mention functions or other callables, add parentheses at the end of their names:
  `subliminal.func()` or `subliminal.Class.method()`.
  This makes the changelog a lot more readable.
- Prefer simple past tense or constructions with "now".
  For example:

  + Added `subliminal.super_cool_func()`.
  + `subliminal.func()` now doesn't crash anymore.
- If you want to reference multiple issues, copy the news fragment to another filename.
  *Towncrier* will merge all news fragments with identical contents into one entry with multiple links to the respective pull requests.

Example entry:

  ```md
  Added `subliminal.super_cool_func()`.
  The feature is really *super cool*.

  ```

`tox run -e changelog` will render the current changelog to the terminal if you have any doubts.

---

*Thanks to Hynek and the [attrs development team](https://github.com/python-attrs/attrs) for the fantastic workflows and documentation, this file was shamelessly modified from theirs.*


[CI]: https://github.com/Diaoul/subliminal/actions?query=workflow%3ACI
[*pre-commit*]: https://pre-commit.com/
[*tox*]: https://tox.wiki/
[semantic newlines]: https://rhodesmill.org/brandon/2012/one-sentence-per-line/
