app_name = "gilson-logs:latest"

build:
	@docker build -t $(app_name) .
run:
	docker run -i \
		-t \
		--rm \
		--env-file=env_file_name \
		-p 8003:8003 \
		-v "/Volumes/npsg/tecan/SourceData/SecondStage/Sample List_Combined_tmp":"/mnt/tsl_dir" \
		-v "/Users/trinhsk/Documents/GitRepos/gilson_comb_wrklst":"/mnt/worklist_dir" \
		$(app_name)
stop:
	@echo "Killing $(app_name) ..."
	@docker ps | grep $(app_name) | awk '{print $1}' | xargs docker stop
