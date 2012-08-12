#!/bin/bash
false
while [ $? -eq 1 ]
do
	python ~/coding/random/ircbot.py
done
