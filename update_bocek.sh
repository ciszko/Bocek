#!/bin/bash
cd /home/pi/Bocek
git fetch
git checkout -f origin/master
systemctl restart bocek.service
echo "Bocek was updated" 
