#!/bin/bash
set -e

echo "Freezing requirements.txt"
pip install pipenv
rm -rf Pipfile* deps
pipenv lock --clear --two --requirements 1>deps
grep '==' deps | sed "s/;\\sextra.*//" > requirements.txt
