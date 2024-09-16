# Release procedure

The git commands assume the following remotes are setup:

* ``origin``: your own fork of the repository.
* ``upstream``: the ``Diaoul/subliminal`` official repository.

## Preparing a new release: Manual method

There are few steps to follow when making a new release:

1. Lint the code, check types, test, check the coverage is high enough
and build and test the documentation.

2. Bump the version number, wherever it is, and update ``HISTORY.rst``
with the changelog fragments.

3. Tag the new version with ``git``.

4. Publish the source distribution and wheel to Pypi.

Although this can all be done manually, there is an automated way,
to limit errors.

## Preparing a new release: Automatic method

We use an automated workflow for releases, that uses GitHub workflows and is triggered
by [manually running](https://docs.github.com/en/actions/managing-workflow-runs/manually-running-a-workflow)
the [prepare-release-pr workflow](https://github.com/Diaoul/subliminal/actions/workflows/prepare-release-pr.yaml)
on GitHub Actions.

1. The automation will decide the new version number based on the following criteria:

- If there is any ``.breaking.rst`` files in the ``changelog.d`` directory, release a new major release
  (e.g. 7.0.0 -> 8.0.0)
- If there are any ``.change.rst`` files in the
  ``changelog.d`` directory, release a new minor release
  (e.g. 7.0.0 -> 7.1.0)
- Otherwise, release a patch release
  (e.g. 7.0.0 -> 7.0.1)
- If the "prerelease" input is set, append the string to the version number
  (e.g. 7.0.0 -> 8.0.0rc1, if "major" is set, and "prerelease" is set to `rc1`)

The choice of the bumped version can be bypassed by the "bump" input
(empty choice means automatic bumped version detection).

2. Trigger the workflow with the following inputs:

   - branch: **main**
   - bump: [**empty**, major, minor, patch]
   - prerelease: empty

Or via the commandline::

    gh workflow run prepare-release-pr.yml -f branch=main -f bump=major -f prerelease=

The automated workflow will publish a PR for a branch ``release-8.0.0``.


## Preparing a new release: Semi-automatic method

To release a version ``MAJOR.MINOR.PATCH-PRERELEASE``, follow these steps:

* Create a branch ``release-MAJOR.MINOR.PATCH-PRERELEASE`` from the ``upstream/main`` branch.

   Ensure your are updated and in a clean working tree.

* Using ``tox``, generate docs, changelog, announcements::

    $ tox -e release -- MAJOR.MINOR.PATCH-PRERELEASE

   This will generate a commit with all the changes ready for pushing.

* Push the ``release-MAJOR.MINOR.PATCH-PRERELEASE`` local branch to the remote
``upstream/release-MAJOR.MINOR.PATCH-PRERELEASE``

* Open a PR for the ``release-MAJOR.MINOR.PATCH-PRERELEASE`` branch targeting ``upstream/main``.


## Releasing

Both automatic and manual processes described above follow the same steps from this point onward.

* After all tests pass and the PR has been approved, merge the PR.
  Merging the PR will trigger the
  [tag-release workflow](https://github.com/Diaoul/subliminal/actions/workflows/tag-release.yaml), that will add a release tag.

  This new tag will then trigger the
  [publish workflow](https://github.com/Diaoul/subliminal/actions/workflows/publish.yaml),
  using the ``release-MAJOR.MINOR.PATCH`` branch as source.

  This job will publish a draft for a Github release.
  When the Github release draft is published, the same workflow will publish to PyPI.
