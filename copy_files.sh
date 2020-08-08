#!/bin/bash
FILE_LIST=(Dockerfile docker-compose.yml gunicorn_config.py oracle_env_vars
requirements.txt app)

CURR_DIR=`pwd`
SHARE_DR="/Volumes/npsg/Gilson/Docker"
for file in ${FILE_LIST[@]};
	do
	if [ $file = "app" ]; then
		cp -R $CURR_DIR/$file $SHARE_DR/;
	else
		if [[ $file != *"__pycache__" ]]; then
			cp $CURR_DIR/$file $SHARE_DR/;
		fi
	fi

	done
