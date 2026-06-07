
from datetime import datetime
from database.models.audit import AuditLog


def log_action(db, action_type, entity_type, entity_id, performed_by, details):

    audit = AuditLog(
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by=performed_by,
        timestamp=datetime.utcnow(),
        details=details
    )

    db.add(audit)

