APP = dadosabertos


ifeq ($(OS), Windows_NT)
    cwd = $(shell echo %CD%)
else
	cwd = $(shell pwd)
endif

build:
	docker build -t $(APP) .

sh:
	@docker run --rm -it -v "$(cwd)":/$(APP) --name work-rfb $(APP) sh
