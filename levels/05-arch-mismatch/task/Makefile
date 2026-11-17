CC     ?= gcc
CFLAGS ?= -O2 -fPIC -shared -Wall

lib: src/mathlib.c
	@mkdir -p build
	$(CC) $(CFLAGS) -o build/libmath.so src/mathlib.c

clean:
	rm -rf build

.PHONY: lib clean
