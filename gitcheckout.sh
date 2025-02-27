#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <branch>"
  exit 1
fi

branch=$1

git checkout $branch
cd akita
git checkout $branch
cd ..