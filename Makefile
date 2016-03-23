run:    build
	@docker run \
	    --rm \
		-ti \
	    ONSdatabaker

build:
	@docker build -t ONSdatabaker .

.PHONY: run build
