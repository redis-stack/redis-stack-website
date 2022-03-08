DEST = ./website
CONTENT = $(DEST)/content/en

.PHONY: init
init:
	git submodule update --init --recursive
	mkdir -p $(CONTENT)

.PHONY: stack
stack:
	python3 build/get_stack.py
	make -C website commands

.PHONY: serve
serve:
	cd website; hugo server --disableFastRender --debug

.PHONY: clean
clean:
	rm -rf $(CONTENT)