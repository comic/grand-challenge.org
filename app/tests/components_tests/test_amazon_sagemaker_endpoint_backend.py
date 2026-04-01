from tests.algorithms_tests.factories import EndpointFactory


class TestEndpointOrchestratorProperties:
    def test_algorithm_model_key(self):
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._algorithm_model_key == (
            f"/auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz"
        )

    def test_algorithm_model_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME = (
            "interactive-algorithms-io"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._algorithm_model_s3_uri == (
            f"s3://interactive-algorithms-io/auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz"
        )

    def test_output_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME = (
            "interactive-algorithms-io"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._output_s3_uri == (
            f"s3://interactive-algorithms-io/io/algorithms/endpoint/{endpoint.pk}/successes"
        )

    def test_failure_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME = (
            "interactive-algorithms-io"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._failure_s3_uri == (
            f"s3://interactive-algorithms-io/io/algorithms/endpoint/{endpoint.pk}/failures"
        )

    def test_endpoint_model_environment(self, settings):
        settings.COMPONENTS_INPUT_BUCKET_NAME = "test_components_input_bucket"
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._model_environment == {
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1",
            "no_proxy": "amazonaws.com",
            "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": "7168",
            "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX": "",
            "GRAND_CHALLENGE_COMPONENT_API_METHOD": endpoint.algorithm_image.api_method,
            "GRAND_CHALLENGE_COMPONENT_MODEL": f"s3://test_components_input_bucket/auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz",
        }

        orchestrator = EndpointFactory.build(algorithm_model=None).orchestrator

        assert (
            "GRAND_CHALLENGE_COMPONENT_MODEL"
            not in orchestrator._model_environment
        )
