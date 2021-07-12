USER_ID = $(shell id -u)
PYTHON_VERSION = 3.8
GDCM_VERSION_TAG = 3.0.6
POETRY_HASH = $(shell shasum -a 512 poetry.lock | cut -c 1-8)
GRAND_CHALLENGE_HTTP_REPOSITORY_URI = public.ecr.aws/m3y0m7n5/grand-challenge/http
GRAND_CHALLENGE_WEB_REPOSITORY_URI = public.ecr.aws/m3y0m7n5/grand-challenge/web
GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI = public.ecr.aws/m3y0m7n5/grand-challenge/web-base
GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI = public.ecr.aws/m3y0m7n5/grand-challenge/web-test-base


build_web_test:
	@docker pull $(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) || { \
		docker buildx build \
			--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
			--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
			--target test-base \
			-t $(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) \
			-f dockerfiles/web-base/Dockerfile \
			.; \
	}
	docker buildx build\
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
		--build-arg COMMIT_ID=$(GIT_COMMIT_ID) \
		--build-arg POETRY_HASH=$(POETRY_HASH) \
		--build-arg GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI) \
		--build-arg GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI) \
		--target test \
		-t $(GRAND_CHALLENGE_WEB_REPOSITORY_URI)-test:$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH) \
		-t $(GRAND_CHALLENGE_WEB_REPOSITORY_URI)-test:latest \
		-f dockerfiles/web/Dockerfile \
		.

build_web_dist:
	@docker pull $(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) || { \
		docker buildx build \
			--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
			--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
			--target base \
			-t $(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH) \
			-f dockerfiles/web-base/Dockerfile \
			.; \
	}
	docker buildx build \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg GDCM_VERSION_TAG=$(GDCM_VERSION_TAG) \
		--build-arg COMMIT_ID=$(GIT_COMMIT_ID) \
		--build-arg POETRY_HASH=$(POETRY_HASH) \
		--build-arg GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI) \
		--build-arg GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI) \
		--target dist \
		-t $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH) \
		-t $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):latest \
		-f dockerfiles/web/Dockerfile \
		.

build_http:
	docker buildx build \
		-t $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH) \
		-t $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):latest \
		dockerfiles/http

push_web_base:
	docker push $(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH)

push_web_test_base:
	docker push $(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(GDCM_VERSION_TAG)-$(POETRY_HASH)

push_web:
	docker push $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH)
	docker push $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):latest

push_http:
	docker push $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(POETRY_HASH)
	docker push $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):latest

build: build_web_test build_web_dist build_http

migrate:
	docker-compose run --rm web python manage.py migrate

migrations:
	docker-compose run -u $(USER_ID) --rm web python manage.py makemigrations

development_fixtures:
	docker-compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts/:ro \
		--rm \
		web \
		bash -c "python manage.py migrate && python manage.py runscript development_fixtures"

create_io_algorithm:
	docker buildx build -t algorithm_io app/tests/resources/gc_demo_algorithm/
	docker save algorithm_io -o app/tests/resources/gc_demo_algorithm/algorithm_io.tar
	chmod a+r app/tests/resources/gc_demo_algorithm/algorithm_io.tar

.PHONY: docs
docs:
	docker-compose run --rm -v `pwd`/docs:/docs -u $(USER_ID) web bash -c "cd /docs && make html"
