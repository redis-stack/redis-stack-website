IP ?= 0.0.0.0
LOGLEVEL ?= INFO
ENV ?= development
HUGO_BUILD ?= --gc --minify
HUGO_SERVER ?= --quiet --disableFastRender -b http://$(IP) --bind $(IP)
DOCKER_IMAGE=image-redis-stack-website
DOCKER_CONTAINER=container-$(DOCKER_IMAGE)
DOCKER_PORT=-p 1313:1313

.PHONY: all init build up clean docker-build docker docker-up docker-sh

ifneq ($(ENV),development)
GET_STATS=--get-stats
endif

ifeq ($(DEBUG),1)
HUGO_DEBUG=--debug --log
LOGLEVEL ?= DEBUG
endif

ifeq ($(SKIP_CLONE),1)
SKIP_CLONE=--skip-clone
endif

all: init build

init:
	@git submodule update --init --recursive

build:
	@python3 build/make_stack.py $(SKIP_CLONE) $(GET_STATS) --loglevel=$(LOGLEVEL)
	@hugo $(HUGO_DEBUG) $(HUGO_BUILD)

up:
	hugo server $(HUGO_DEBUG) $(HUGO_SERVER) --environment $(ENV)

clean:
	@rm -f data/*.json
	@rm -rf content public tmp

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
