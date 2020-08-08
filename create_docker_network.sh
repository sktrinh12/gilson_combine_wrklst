#!/bin/bash

if [ $# -eq 0 ]; then
	echo "no arguments supplied, need to indicate the subnet and gateway for
	server or local machines (i.e. 1 or 12 for 192.168.0.1)"
else
	if [[ $# -eq 1 ]]; then
		if (( $1 >= 0 && $1 <= 24)); then
			docker network create -d bridge --subnet 192.168.$1.0/24 --gateway 192.168.$1.$1 gilsonappnet
			# echo "docker network create -d bridge --subnet 192.168.$1.0/24 --gateway 192.168.$1.$1 gilsonappnet"
		else
			echo "range between 1-24"
		fi
	else
		echo "needs to be only one argument"
	fi
fi
