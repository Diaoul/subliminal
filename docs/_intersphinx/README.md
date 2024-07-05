# Creating a Custom Intersphinx Mapping

Copied from [exhale documentation.](https://github.com/svenevs/exhale/blob/master/docs/_intersphinx/README.md)

## The Issue

The BeautifulSoup intersphinx mapping does not work; see [bug here][bug].

[bug]: https://bugs.launchpad.net/beautifulsoup/+bug/1453370

So we'll just do it manually.

## The Tool

Use the tool `sphobjinv` to do this (`pip install sphobjinv`).

- [Explanation of syntax][syntax].

[syntax]: https://sphinx-objectsinv-encoderdecoder.readthedocs.io/en/latest/syntax.html

## How to Reproduce

1. Downloaded original objects.inv from bs4 docs

   ```console
   $ curl -O https://www.crummy.com/software/BeautifulSoup/bs4/doc/objects.inv
   $ mv objects.inv bs4_objects.inv
   ```

2. Converted that bad boy to human readable (the file `bs4_objects.txt`).

   ```console
   $ sphobjinv convert plain bs4_objects.inv bs4_objects.txt
   ```

3. Any time I have a class I want to add a reference for, just add that line to
   `bs4_objects.txt`.  Recall that there is a specific [syntax][syntax] associated
   with these files.

4. When you add a new line, simply run (assuming you are in this directory)

    ```console
    $ sphobjinv convert zlib bs4_objects.txt bs4_objects.inv
    ```

5. Re-run sphinx, usually you need to clean it for the doctree index to be rebuilt.

   ```console
   $ make clean html
   ```

## Note

These changes apply because we have **2** things in `conf.py`:

1. In the `extensions` list, we have `"sphinx.ext.intersphinx"`.
2. We have configured our intersphinx mapping to point to here (as opposed to the
   one being hosted online):

   ```py
   intersphinx_mapping = {
      'bs4':    ('https://www.crummy.com/software/BeautifulSoup/bs4/doc/', "_intersphinx/bs4_objects.inv")
   }
   ```

## In the Documentation

So now we can do something like

```rst
- See :class:`bs4.BeautifulSoup`
- See :meth:`bs4.BeautifulSoup.get_text`
- See :class:`bs4.element.Tag`
```

because we added the following line to our `bs4_objects.txt`:

```
bs4.BeautifulSoup           py:class  1 index.html#beautifulsoup -
bs4.BeautifulSoup.get_text  py:method 1 index.html#get-text      -
bs4.element.Tag             py:class  1 index.html#tag           -
```
