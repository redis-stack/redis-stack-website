DEST = ./website
CONTENT = $(DEST)/content/en

.PHONY: init
init:
	git submodule update --init --recursive
	mkdir -p $(CONTENT)

.PHONY: stack
stack:
	cd $(DEST); git restore .
	python3 build/get_stack.py
	make -C $(DEST) commands

.PHONY: serve
serve:
	cd $(DEST); hugo server --disableFastRender --debug

.PHONY: clean
clean:
	cd $(DEST); git restore .
	rm -rf $(CONTENT)