import os
import unittest
from unittest.mock import patch

from services.query_service import QueryService
from src.runtime.config import RuntimeConfig


class _PipelineStub:
    instances = []

    def __init__(self, runtime_config):
        self.runtime_config = runtime_config
        self.warmup_calls = 0
        self.__class__.instances.append(self)

    def warm_up_retrieval(self):
        self.warmup_calls += 1


class QueryServiceWarmupTests(unittest.TestCase):
    def setUp(self):
        _PipelineStub.instances.clear()

    def test_retrieval_is_prewarmed_by_default(self):
        with patch("services.query_service.QuerionyxPipelineV3", _PipelineStub):
            with patch.dict(os.environ, {"QUERIONYX_PREWARM_RETRIEVAL": "1"}):
                service = QueryService(runtime_config=RuntimeConfig())

        self.assertEqual(_PipelineStub.instances[0].warmup_calls, 1)
        self.assertEqual(service.retrieval_warmup["status"], "ready")
        self.assertGreaterEqual(service.retrieval_warmup["latency_ms"], 0.0)

    def test_retrieval_prewarm_can_be_disabled(self):
        with patch("services.query_service.QuerionyxPipelineV3", _PipelineStub):
            with patch.dict(os.environ, {"QUERIONYX_PREWARM_RETRIEVAL": "0"}):
                service = QueryService(runtime_config=RuntimeConfig())

        self.assertEqual(_PipelineStub.instances[0].warmup_calls, 0)
        self.assertEqual(service.retrieval_warmup, {"status": "disabled", "latency_ms": 0.0})


if __name__ == "__main__":
    unittest.main()
