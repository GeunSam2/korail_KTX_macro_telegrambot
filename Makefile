IMAGE_NAME := geunsam2/korailbot:v3
UNAME_S := $(shell uname -s)
PYTHON_VERSION := $(shell sed -n 's/^python_version *= *"\(.*\)"/\1/p' Pipfile)

help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

.PHONY: setup
setup:			## Setup development environment (install pipenv if needed)
	@command -v pipenv >/dev/null 2>&1 || { \
		echo "Installing pipenv..."; \
		if [ "$(UNAME_S)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then \
			brew install pipenv; \
		elif command -v pipx >/dev/null 2>&1; then \
			pipx install pipenv; \
		else \
			python3 -m pip install --user pipenv || \
				python3 -m pip install --user --break-system-packages pipenv; \
		fi; \
	}
	@command -v pipenv >/dev/null 2>&1 || \
		echo "경고: pipenv가 PATH에 없습니다. ~/.local/bin 을 PATH에 추가하세요."
	@command -v pyenv >/dev/null 2>&1 || { \
		if [ "$(UNAME_S)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then \
			echo "Installing pyenv..."; brew install pyenv; \
		else \
			echo "참고: pyenv가 없습니다 (선택 사항)."; \
			echo "  Python $(PYTHON_VERSION) 가 필요하면 설치하세요: curl -fsSL https://pyenv.run | bash"; \
		fi; \
	}

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

.PHONY: test
test:			## Run all tests with pytest
	pipenv run pytest tests/ -v

.PHONY: test-api
test-api:		## Run API endpoint tests only
	pipenv run pytest tests/test_api.py -v

.PHONY: test-logic
test-logic:		## Run Korail logic tests only
	pipenv run pytest tests/test_korail_logic.py -v

.PHONY: build
build:			## Build Docker Image
	docker build -t ${IMAGE_NAME} .

.PHONY: publish
publish: build	## Publish Docker Image
	docker push ${IMAGE_NAME}
