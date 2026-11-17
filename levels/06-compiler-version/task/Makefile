CXX      ?= g++
CXXFLAGS ?= -std=c++23 -O2 -Wall

build/app: src/main.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o build/app src/main.cpp

build: build/app

run: build
	./build/app

clean:
	rm -rf build

.PHONY: build run clean
