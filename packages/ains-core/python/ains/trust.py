from .db import SessionLocal, TrustRecord

def calculate_trust_score(agent_id: str) -> float:
    session = SessionLocal()
    record = session.query(TrustRecord).filter_by(agent_id=agent_id).first()
    if not record:
        session.close()
        return 50.0

    try:
        rep = (record.successful_transactions /
               (record.successful_transactions + record.failed_transactions)) * (record.rating / 5) * 100
    except ZeroDivisionError:
        rep = 50.0

    uptime = (record.uptime_30d + record.uptime_90d + record.uptime_all_time) / 3
    performance = 100 - (record.avg_latency_ms / 1000 * 100)

    trust_score = (rep * 0.6) + (uptime * 0.3) + (performance * 0.1)
    session.close()
    return trust_score


def update_trust_score(agent_id: str):
    session = SessionLocal()
    record = session.query(TrustRecord).filter_by(agent_id=agent_id).first()
    if not record:
        session.close()
        return
    record.trust_score = calculate_trust_score(agent_id)
    session.commit()
    session.close()
