DEST = ./website
CONTENT = $(DEST)/content/en

.PHONY: all
all: init redis redisjson
	cd $(DEST); hugo
	#  redisearch redisgraph redistimeseries redisbloom redisbloom

.PHONY: init
init:
	git submodule update --init --recursive
	mkdir -p $(CONTENT)

.PHONY: redis
redis:
	REDIS_DOC=`pwd`/../redis-doc make -C redis-stack-website theme commands

.PHONY: redisjson
redisjson:
	mkdir -p $(CONTENT)/redisjson
	cp ../redisjson/commands.json $(CONTENT)/redisjson/
	cp -r ../redisjson/docs/* $(CONTENT)/redisjson/
	python3 $(DEST)/build/process_commands.py "$(CONTENT)/redisjson/commands.json" "$(CONTENT)/redisjson/commands"

.PHONY: prepare
prepare:
	REDIS_DOC=/tmp/redis-doc make -C redis-stack-website theme sources all
