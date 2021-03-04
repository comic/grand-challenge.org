USER_ID = $(shell id -u)
export DOCKER_BUILDKIT = 1
PYTHON_VERSION = 3.8
GDCM_VERSION_TAG = 3.0.6
POETRY_HASH = $(shell shasum -a 512 poetry.lock | cut -c 1-8)

build_web_test:
	@docker pull grandchallenge/web-test-base:$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) || { \
		docker build \
			--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
			--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
			--target test-base \
			-t grandchallenge/web-test-base:$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) \
			-f dockerfiles/web-base/Dockerfile \
			.; \
	}
	docker build \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
		--build-arg COMMIT_ID=$(GIT_COMMIT_ID) \
		--build-arg POETRY_HASH=$(POETRY_HASH) \
		--target test \
		-t grandchallenge/web-test:$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH) \
		-t grandchallenge/web-test:latest \
		-f dockerfiles/web/Dockerfile \
		.

build_web_dist:
	@docker pull grandchallenge/web-base:$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) || { \
		docker build \
			--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
			--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
			--target base \
			-t grandchallenge/web-base:$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) \
			-f dockerfiles/web-base/Dockerfile \
			.; \
	}
	docker build \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
		--build-arg COMMIT_ID=$(GIT_COMMIT_ID) \
		--build-arg POETRY_HASH=$(POETRY_HASH) \
		--target dist \
		-t grandchallenge/web:$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH) \
		-t grandchallenge/web:latest \
		-f dockerfiles/web/Dockerfile \
		.

build_http:
	docker build \
		-t grandchallenge/http:$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH) \
		-t grandchallenge/http:latest \
		dockerfiles/http

push_web_base:
	docker push grandchallenge/web-base:$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH)

push_web_test_base:
	docker push grandchallenge/web-test-base:$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH)

push_web:
	docker push grandchallenge/web:$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH)
	docker push grandchallenge/web:latest

push_http:
	docker push grandchallenge/http:$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH)
	docker push grandchallenge/http:latest

build: build_web_test build_web_dist build_http

push: push_web_base push_web_test_base push_web push_http

migrations:
	docker-compose run -u $(USER_ID) --rm web python manage.py makemigrations

.PHONY: docs
docs:
	docker-compose run --rm -v `pwd`/docs:/docs -u $(USER_ID) web bash -c "cd /docs && make html"
