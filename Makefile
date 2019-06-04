USER_ID = $(shell id -u)

build_web:
	docker build \
		--target test \
		-t grandchallenge/web-test:$(BUILD_BUILDID)-$(BUILD_SOURCEBRANCHNAME) \
		-t grandchallenge/web-test:latest \
		-f dockerfiles/web/Dockerfile \
		.
	docker build \
		--target dist \
		-t grandchallenge/web:$(BUILD_BUILDID)-$(BUILD_SOURCEBRANCHNAME) \
		-t grandchallenge/web:latest \
		-f dockerfiles/web/Dockerfile \
		.

build_http:
	docker build \
		-t grandchallenge/http:$(BUILD_BUILDID)-$(BUILD_SOURCEBRANCHNAME) \
		-t grandchallenge/http:latest \
		dockerfiles/http

build: build_web build_http

push_web:
	docker push grandchallenge/web:$(BUILD_BUILDID)-$(BUILD_SOURCEBRANCHNAME)

push_http:
	docker push grandchallenge/http:$(BUILD_BUILDID)-$(BUILD_SOURCEBRANCHNAME)

push: push_web push_http

migrations:
	docker-compose run -u $(USER_ID) --rm web python manage.py makemigrations
