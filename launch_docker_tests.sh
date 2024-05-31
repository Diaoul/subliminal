#!/bin/sh
cd /tests/
pip install -e .[test]
pytest