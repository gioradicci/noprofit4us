from repositories.dashboard_repository import (
    count_active_members,
    count_unpaid_memberships,
    total_income,
    count_pending_users,
    count_renewals
)


def get_treasurer_dashboard(db):

    active = count_active_members(db)
    unpaid = count_unpaid_memberships(db)
    income = total_income(db)
    pending = count_pending_users(db)
    renewals = count_renewals(db)

    return {
        "active_members": active,
        "unpaid_memberships": unpaid,
        "total_income": income or 0,
        "pending_applications": pending,
        "renewals": renewals
    }