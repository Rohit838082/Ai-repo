CXX = g++
CXXFLAGS = -std=c++17 -O3

all: builder

builder: builder.cpp
	$(CXX) $(CXXFLAGS) -o builder builder.cpp

clean:
	rm -f builder output_artifact.zip
	rm -rf build_workspace
