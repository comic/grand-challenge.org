USER_ID=$(shell id -u)
PYTHON_VERSION="3.11"
LOCKFILE_HASH=$(shell shasum -a 512 uv.lock | cut -c 1-8)
GIT_COMMIT_ID=$(shell git describe --always --dirty)
GIT_BRANCH_NAME=$(shell git rev-parse --abbrev-ref HEAD | sed "s/[^[:alnum:]]//g")
GRAND_CHALLENGE_HTTP_REPOSITORY_URI=public.ecr.aws/diag-nijmegen/grand-challenge/http
GRAND_CHALLENGE_WEB_REPOSITORY_URI=public.ecr.aws/diag-nijmegen/grand-challenge/web
GRAND_CHALLENGE_WEB_TEST_REPOSITORY_URI=public.ecr.aws/diag-nijmegen/grand-challenge/web-test
GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI=public.ecr.aws/diag-nijmegen/grand-challenge/web-base
GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI=public.ecr.aws/diag-nijmegen/grand-challenge/web-test-base


build_web_test:
	@docker pull $(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(LOCKFILE_HASH) || { \
		docker buildx build \
			--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
			--target test-base \
			-t $(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(LOCKFILE_HASH) \
			-f dockerfiles/web-base/Dockerfile \
			.; \
	}
	docker buildx build\
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg COMMIT_ID=$(GIT_COMMIT_ID) \
		--build-arg LOCKFILE_HASH=$(LOCKFILE_HASH) \
		--build-arg GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI) \
		--build-arg GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI) \
		--target test \
		-t $(GRAND_CHALLENGE_WEB_TEST_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(LOCKFILE_HASH) \
		-t $(GRAND_CHALLENGE_WEB_TEST_REPOSITORY_URI):latest \
		-f dockerfiles/web/Dockerfile \
		.

build_web_dist:
	@docker pull $(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(LOCKFILE_HASH) || { \
		docker buildx build \
			--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
			--target base \
			-t $(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(LOCKFILE_HASH) \
			-f dockerfiles/web-base/Dockerfile \
			.; \
	}
	DOCKER_BUILDKIT=0 docker build \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg COMMIT_ID=$(GIT_COMMIT_ID) \
		--build-arg LOCKFILE_HASH=$(LOCKFILE_HASH) \
		--build-arg GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI) \
		--build-arg GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI=$(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI) \
		--network grand-challengeorg_default \
		--target dist \
		-t $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(LOCKFILE_HASH) \
		-t $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):latest \
		-f dockerfiles/web/Dockerfile \
		.

build_http:
	docker buildx build \
		-t $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(LOCKFILE_HASH) \
		-t $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):latest \
		dockerfiles/http

push_web_base:
	docker push $(GRAND_CHALLENGE_WEB_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(LOCKFILE_HASH)

push_web_test_base:
	docker push $(GRAND_CHALLENGE_WEB_TEST_BASE_REPOSITORY_URI):$(PYTHON_VERSION)-$(LOCKFILE_HASH)

push_web:
	docker push $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(LOCKFILE_HASH)
	docker push $(GRAND_CHALLENGE_WEB_REPOSITORY_URI):latest

push_http:
	docker push $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):$(GIT_COMMIT_ID)-$(GIT_BRANCH_NAME)-$(LOCKFILE_HASH)
	docker push $(GRAND_CHALLENGE_HTTP_REPOSITORY_URI):latest

build: build_web_test build_web_dist build_http

migrate:
	docker compose run --rm web python manage.py migrate

check_migrations:
	docker compose run --rm web python manage.py makemigrations --dry-run --check

migrations:
	docker compose run -u $(USER_ID) --rm web python manage.py makemigrations

runserver: build_web_test build_http development_fixtures build_dev_js_libraries
	bash -c "trap 'docker compose down' EXIT; docker compose up"

rundeps:
	bash -c "trap 'docker compose down' EXIT; docker compose up postgres minio.localhost redis registry"

minio:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		web \
		bash -c "python manage.py runscript minio"

build_dev_js_libraries:
	bash -c "cd app && npm install && npm run build"

development_fixtures:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		celery_worker \
		bash -c "python manage.py migrate && python manage.py runscript minio development_fixtures"

algorithm_evaluation_fixtures:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		celery_worker \
		python manage.py runscript algorithm_evaluation_fixtures

external_algorithm_evaluation_fixtures:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		celery_worker_evaluation \
		python manage.py runscript external_algorithm_evaluation_fixtures

cost_fixtures:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		celery_worker \
		python manage.py runscript cost_fixtures

component_interface_value_fixtures:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		celery_worker \
		python manage.py runscript component_interface_value_fixtures

superuser:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		web \
		python manage.py runscript create_superuser

docpages:
	docker compose run \
		-v $(shell readlink -f ./scripts/):/app/scripts:ro \
		--rm \
		web \
		python manage.py runscript create_docpages

.PHONY: docs
docs:
	docker compose run --rm -u $(USER_ID) web bash -c "cd docs && make html"
