OUT ?= _site

.PHONY: all serve clean

all:
	python3 site/build.py --out $(OUT)

serve: all
	python3 -m http.server --directory $(OUT) 8000

clean:
	rm -rf $(OUT)
