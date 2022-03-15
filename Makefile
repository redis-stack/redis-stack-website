DEST ?= ./content/en
IP ?= 0.0.0.0
PY_LOGLEVEL ?= INFO

.PHONY: all init build up clean docker-build docker docker-up docker-sh

ifeq ($(DEBUG),1)
HUGO_DEBUG=--debug
PY_LOGLEVEL=DEBUG
endif

ifeq ($(SKIP_CLONE),1)
SKIP_CLONE=--skip-clone
endif

DOCKER_IMAGE=image-redis-stack-website
DOCKER_CONTAINER=container-$(DOCKER_IMAGE)
DOCKER_PORT=-p 1313:1313

all: init build

init:
	@git submodule update --init --recursive 

build: export LOGLEVEL=$(PY_LOGLEVEL)
build:
	@python3 build/make_stack.py $(SKIP_CLONE)
	@hugo $(HUGO_DEBUG) --print-mem --gc --minify

up:
	hugo server --disableFastRender $(HUGO_DEBUG) -b http://$(IP) --bind $(IP)

clean:
	@rm -f data/groups.json data/commands.json
	@rm -f static/js/cli.js static/css/cli.css
	@rm -rf $(DEST)/*
	@rm -rf public

ifneq ($(VOL),)
DOCKER_VOL=-v $(VOL):$(VOL)
endif

docker-build:
	@docker build -t $(DOCKER_IMAGE) --build-arg PRIVATE_REPOS_PAT=$(PRIVATE_REPOS_PAT) .

docker docker-up: docker-build
	@docker run -it $(DOCKER_PORT) $(DOCKER_IMAGE) make up

docker-sh:
	@docker run -it $(DOCKER_PORT) $(DOCKER_VOL) $(DOCKER_IMAGE) bash

docker-all: docker-build
	@docker create --name $(DOCKER_CONTAINER) $(DOCKER_IMAGE) 
	@docker cp $(DOCKER_CONTAINER):/build/public - > public.tar
	@docker rm -v $(DOCKER_CONTAINER)
	@tar xvf public.tar
	@rm public.tar