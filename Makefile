IMAGE_NAME := geunsam2/korailbot:v3

help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

.PHONY: setup
setup:			## Setup development environment (install pipenv if needed)
	@command -v pipenv >/dev/null 2>&1 || { echo "Installing pipenv..."; brew install pipenv; }
	@command -v pyenv >/dev/null 2>&1 || { echo "Installing pyenv..."; brew install pyenv; }

.PHONY: install
install:		## Install dependencies with pipenv
	pipenv install

.PHONY: run
run:			## Run the application locally
	pipenv run python src/app.py

.PHONY: shell
shell:			## Open pipenv shell
	pipenv shell

.PHONY: requirements
requirements:	## Generate requirements.txt from Pipfile.lock (for Docker)
	pipenv requirements > requirements.txt
	echo "uwsgi==2.0.31" >> requirements.txt

.PHONY: build
build:			## Build Docker Image
	docker build -t ${IMAGE_NAME} .

.PHONY: publish
publish: build	## Publish Docker Image
	docker push ${IMAGE_NAME}
