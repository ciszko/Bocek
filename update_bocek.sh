#!/bin/bash
git fetch
git checkout -f origin/master
systemctl restart bocek.service
echo "Bocek was updated" 
