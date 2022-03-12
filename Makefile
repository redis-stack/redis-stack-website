DEST ?= ./content/en
IP ?= 0.0.0.0
PY_LOGLEVEL ?= INFO

.PHONY: all init stack build serve up clean docker docker-sh

ifeq ($(DEBUG),1)
HUGO_DEBUG=--debug
PY_LOGLEVEL=DEBUG
endif

ifeq ($(SKIP_CLONE),1)
SKIP_CLONE=--skip-clone
endif

DOCKER_IMAGE=redis-stack-docs
DOCKER_PORT=-p 1313:1313

all: init build

init:
	@git submodule update --init --recursive themes/docsy
	@git submodule update --init themes/redis

stack build: export LOGLEVEL=$(PY_LOGLEVEL)
stack build:
	@cp themes/redis/data/groups.json data
	@python3 build/get_stack.py $(SKIP_CLONE)
	@python3 themes/redis/build/process_commands.py "$(DEST)/commands.json" "$(DEST)/commands"

serve up:
	hugo server --disableFastRender $(HUGO_DEBUG) -b http://$(IP) --bind $(IP)

clean:
	@rm data/groups.json
	@rm -rf $(DEST)/*

docker:
	@docker build -t $(DOCKER_IMAGE) .
	@docker run -it $(DOCKER_PORT) $(DOCKER_IMAGE)

ifneq ($(VOL),)
DOCKER_VOL=-v $(VOL):$(VOL)
endif

docker-sh:
	@docker run -it $(DOCKER_PORT) $(DOCKER_VOL) $(DOCKER_IMAGE) bash
