#!/bin/bash
# Deploy installers to switchdrive
# Calling syntax:
#
#     bash deploy_switchdrive.sh user:password filename

first=""
REPO=`basename $TRAVIS_REPO_SLUG`
for arg in $@; do
    if [[ $first == "" ]]; then
        first=False
    else
        curl -X PUT -u $1 "https://drive.switch.ch/remote.php/webdav/$REPO/$TRAVIS_BRANCH/$arg" --data-binary @$arg
    fi
done
