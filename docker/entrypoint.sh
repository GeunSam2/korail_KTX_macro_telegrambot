#!/bin/bash

jupyter notebook --allow-root --ip 0.0.0.0 &
python /source/app.py &
sleep infinity
