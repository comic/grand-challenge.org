USER_ID = $(shell id -u)

build_web:
	docker build \
		--target test \
		-t grandchallenge/web-test:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH_SAFE) \
		-t grandchallenge/web-test:latest \
		-f dockerfiles/web/Dockerfile \
		.
	docker build \
		--target dist \
		-t grandchallenge/web:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH_SAFE) \
		-t grandchallenge/web:latest \
		-f dockerfiles/web/Dockerfile \
		.

build_http:
	docker build \
		-t grandchallenge/http:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH_SAFE) \
		-t grandchallenge/http:latest \
		dockerfiles/http

build: build_web build_http

push_web:
	docker push grandchallenge/web:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH_SAFE)

push_http:
	docker push grandchallenge/http:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH_SAFE)

push: push_web push_http

migrations:
	docker-compose run -u $(USER_ID) --rm web python manage.py makemigrations

.PHONY: docs
docs:
	docker-compose run --rm -v `pwd`/docs:/docs -u $(USER_ID) web bash -c "cd /docs && make html"
