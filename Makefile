USER_ID = $(shell id -u)

build:
	docker build \
		--target base \
		-t grandchallenge/web:$(TRAVIS_BUILD_NUMBER) \
		-t grandchallenge/web:latest \
		-f dockerfiles/web/Dockerfile \
		.
	docker build \
		--build-arg PIPENV_DEV=--dev \
		-t grandchallenge/web-test:$(TRAVIS_BUILD_NUMBER) \
		-t grandchallenge/web-test:latest \
		-f dockerfiles/web/Dockerfile \
		.
	docker build \
		-t grandchallenge/http:$(TRAVIS_BUILD_NUMBER) \
		-t grandchallenge/http:latest \
		dockerfiles/http

push:
	docker push grandchallenge/http:$(TRAVIS_BUILD_NUMBER)
	docker push grandchallenge/web:$(TRAVIS_BUILD_NUMBER)

migrations:
	docker-compose run -u $(USER_ID) --rm web python manage.py makemigrations
