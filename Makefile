DEST = website
CONTENT = $(DEST)/content/en
IP ?= 0.0.0.0

.PHONY: all init stack build serve up clean docker docker-sh

ifeq ($(DEBUG),1)
HUGO_DEBUG=--debug
endif

DOCKER_IMAGE=redis-stack-docs
DOCKER_PORT=-p 1313:1313

all: init build

init:
	@git submodule update --init --recursive
	@mkdir -p $(CONTENT)

stack build:
	@cd $(DEST); git restore .
	@python3 build/get_stack.py
	@make -C $(DEST) commands

serve up:
	@cd $(DEST); hugo server --disableFastRender $(HUGO_DEBUG) -b http://$(IP) --bind $(IP)

clean:
	@cd $(DEST); git restore .
	@rm -rf $(CONTENT)

docker:
	@docker build -t $(DOCKER_IMAGE) .
	@docker run -it $(DOCKER_PORT) $(DOCKER_IMAGE)

ifneq ($(VOL),)
DOCKER_VOL=-v $(VOL):$(VOL)
endif

docker-sh:
	@docker run -it $(DOCKER_PORT) $(DOCKER_VOL) $(DOCKER_IMAGE) bash
