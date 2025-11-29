import pytest; from datetime import datetime
class MockMetrics:
    def __init__(self): self.data = {}
    def get_metrics(self, agent_id):
        if agent_id not in self.data:
            class M: trust_score=0.5; avg_latency=0.0; success_rate=1.0; request_count=0; last_seen=datetime.now()
            self.data[agent_id]=M()
        return self.data[agent_id]
def test_metrics_collection():
    from aicp.metrics import MetricsCollector; c=MetricsCollector(); c.record_success("a",0.5); m=c.get_metrics("a")
    assert m.request_count==1 and m.success_count==1 and m.avg_latency==0.5; print("✅ Metrics")
def test_round_robin():
    from aicp.routing_strategies import RoundRobinRouter; r=RoundRobinRouter({"a":{"capabilities":["x"]},"b":{"capabilities":["x"]}},MockMetrics())
    s=[r.select_agent("x") for _ in range(4)]; assert s==["a","b","a","b"]; print("✅ Round-robin")
def test_least_loaded():
    from aicp.routing_strategies import LeastLoadedRouter; r=LeastLoadedRouter({"a":{"capabilities":["x"]},"b":{"capabilities":["x"]}},MockMetrics())
    r.pending_tasks["a"]=5; r.pending_tasks["b"]=2; assert r.select_agent("x")=="b"; print("✅ Least-loaded")
def test_trust_weighted():
    from aicp.routing_strategies import TrustWeightedRouter; m=MockMetrics(); m.get_metrics("a").trust_score=0.9; m.get_metrics("b").trust_score=0.1
    r=TrustWeightedRouter({"a":{"capabilities":["x"]},"b":{"capabilities":["x"]}},m); s=[r.select_agent("x") for _ in range(100)]
    assert s.count("a")>70; print("✅ Trust-weighted")
def test_performance():
    from aicp.routing_strategies import PerformanceBasedRouter; m=MockMetrics(); m.get_metrics("a").avg_latency=0.5; m.get_metrics("b").avg_latency=0.1
    r=PerformanceBasedRouter({"a":{"capabilities":["x"]},"b":{"capabilities":["x"]}},m); assert r.select_agent("x")=="b"; print("✅ Performance")
def test_error():
    from aicp.routing_strategies import RoundRobinRouter; r=RoundRobinRouter({"a":{"capabilities":["y"]}},MockMetrics())
    with pytest.raises(ValueError): r.select_agent("x"); print("✅ Error handling")
if __name__=="__main__":
    test_metrics_collection(); test_round_robin(); test_least_loaded(); test_trust_weighted(); test_performance(); test_error(); print("✅ All tests!")
