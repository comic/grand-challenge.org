USER_ID = $(shell id -u)

build:
	docker build \
		--target test \
		-t grandchallenge/web-test:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH) \
		-t grandchallenge/web-test:latest \
		-f dockerfiles/web/Dockerfile \
		.
	docker build \
		--target dist \
		-t grandchallenge/web:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH) \
		-t grandchallenge/web:latest \
		-f dockerfiles/web/Dockerfile \
		.
	docker build \
		-t grandchallenge/http:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH) \
		-t grandchallenge/http:latest \
		dockerfiles/http

push:
	docker push grandchallenge/http:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH)
	docker push grandchallenge/web:$(TRAVIS_BUILD_NUMBER)-$(TRAVIS_BRANCH)

migrations:
	docker-compose run -u $(USER_ID) --rm web python manage.py makemigrations
