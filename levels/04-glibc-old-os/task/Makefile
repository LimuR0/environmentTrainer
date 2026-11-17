CC      ?= gcc
CFLAGS  ?= -O2 -Wall

build/tool: src/tool.c
	@mkdir -p build
	$(CC) $(CFLAGS) -o build/tool src/tool.c

build: build/tool

clean:
	rm -rf build

.PHONY: build clean
