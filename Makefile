IMAGE_NAME := geunsam2/korailbot:v3

help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

.PHONY: mac-setup
install:	## Setup your mac to use this python enviroment
	brew install pipenv
	brew install pyenv
	pipenv install

.PHONY: publish
publish:		## Run the server
	docker build -t ${IMAGE_NAME} -f docker/Dockerfile .
	docker push ${IMAGE_NAME}
