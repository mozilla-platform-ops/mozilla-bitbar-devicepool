#!/bin/bash

# virtualenv
# search_string="main.py"
# poetry
search_string="start-test-run-manager"

pkill -USR2 -f "$search_string"
while pkill -0 -f "$search_string"; do
    sleep 1
done
