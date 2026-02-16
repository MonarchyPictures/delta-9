from app.models.notification import Notification

def create_notification(db, agent, lead_count):

    if lead_count == 0:
        return

    notification = Notification(
        agent_id=agent.id,
        message=f"{lead_count} new leads found for '{agent.name}'",
        lead_count=lead_count,
    )

    db.add(notification)
    db.commit()
