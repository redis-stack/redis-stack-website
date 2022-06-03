STACK_MODULE ?= "*"
IP ?= 0.0.0.0
LOGLEVEL ?= INFO
ENV ?= development
HUGO_CONTENT ?= ./content/en
HUGO_BUILD ?= --gc --minify
HUGO_SERVER ?= --quiet --disableFastRender -b http://$(IP) --bind $(IP)
DOCKER_IMAGE=image-redis-stack-website
DOCKER_CONTAINER=container-$(DOCKER_IMAGE)
DOCKER_PORT=-p 1313:1313

.PHONY: all init build up clean docker-build docker-make docker docker-up docker-sh netlify

ifeq ($(ENV),production)
GET_META=--production
endif

ifeq ($(DEBUG),1)
HUGO_DEBUG=--debug --log
LOGLEVEL ?= DEBUG
endif

ifeq ($(SKIP_CLONE),1)
SKIP_CLONE=--skip-clone
endif

all: build

build:
	# @python3 build/get_meta.py $(GET_META) --loglevel=$(LOGLEVEL)
	@python3 build/make_stack.py $(SKIP_CLONE) --module=$(STACK_MODULE) --loglevel=$(LOGLEVEL)
	@cp -R data/*.json $(HUGO_CONTENT)
	@hugo $(HUGO_DEBUG) $(HUGO_BUILD)

up:
	hugo server $(HUGO_DEBUG) $(HUGO_SERVER) -w --environment $(ENV)

clean:
	@rm -f config.toml
	# @rm -f data/*.json
	@rm -rf $(HUGO_CONTENT) assets layouts public static resources tmp

ifneq ($(VOL),)
DOCKER_VOL=-v $(VOL):$(VOL)
endif

docker-build:
	@docker build -t $(DOCKER_IMAGE) .

docker-make: docker-build
	@docker run -t \
		--env PRIVATE_ACCESS_TOKEN=$(PRIVATE_ACCESS_TOKEN) \
		--env SKIP_CLONE=$(SKIP_CLONE) \
		--env GET_STATS=$(GET_STATS) \
		--env LOGLEVEL=$(LOGLEVEL) \
		--env STACK_MODULE=$(STACK_MODULE) \
		$(DOCKER_IMAGE) make clean build

docker docker-up: docker-make
	@docker run -it $(DOCKER_PORT) $(DOCKER_IMAGE) make up

docker-sh:
	@docker run -it $(DOCKER_PORT) $(DOCKER_VOL) $(DOCKER_IMAGE) bash

docker-all: docker-build docker-make
	@docker create --name $(DOCKER_CONTAINER) $(DOCKER_IMAGE)
	@docker cp $(DOCKER_CONTAINER):/build/public - > public.tar
	@docker rm -v $(DOCKER_CONTAINER)
	@rm -rf public/
	@tar xvf public.tar
	@rm public.tar

netlify:
	@echo "INCOMING_HOOK_BODY: $(INCOMING_HOOK_BODY)"
	@make all
	@cp _redirects public
