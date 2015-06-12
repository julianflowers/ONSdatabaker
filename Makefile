run:    build
	@docker run \
	    --rm \
		-ti \
	    databaker

build:
	@docker build -t databaker .

bind:   build
	@docker run \
		-u $(shell id -u):$(shell id -g) \
		-v $$PWD:/home/nobody \
		-v /etc/passwd:/etc/passwd \
		-v /etc/group:/etc/group \
		--rm \
		-ti \
		databaker

.PHONY: run build bind
