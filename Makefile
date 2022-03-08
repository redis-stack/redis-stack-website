DEST = ./website
CONTENT = $(DEST)/content/en
IP ?= 0.0.0.0

.PHONY: init
init:
	@git submodule update --init --recursive
	@mkdir -p $(CONTENT)

.PHONY: stack
stack:
	@cd $(DEST); git restore .
	@python3 build/get_stack.py
	@make -C $(DEST) commands

.PHONY: serve
serve:
	@cd $(DEST); hugo server --disableFastRender --debug -b http://$(IP) --bind $(IP)

.PHONY: clean
clean:
	@cd $(DEST); git restore .
	@rm -rf $(CONTENT)

.PHONY: docker
docker:
	@docker build -t redis-stack-docs .
	@docker run -it -p 1313:1313 redis-stack-docs

.PHONY: docker-sh
docker-sh:
	@docker run -it -p 1313:1313 redis-stack-docs bash
