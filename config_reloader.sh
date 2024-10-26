#!/bin/bash

CONFIG_DIR="./nginx"

inotifywait -m -r -e modify,create,delete "$CONFIG_DIR" | while read path action file; do
    echo "$(date): Detected $action on $file"
    nginx -t && sudo nginx -s reload
done
