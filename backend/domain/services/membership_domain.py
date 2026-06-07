from datetime import date


def calculate_membership_period(start_date: date):
    if start_date.month >= 11:
        end_year = start_date.year + 1
    else:
        end_year = start_date.year

    return start_date, date(end_year, 12, 31)


def calculate_reference_year(start_date: date):
    if start_date.month >= 11:
        return start_date.year + 1
    else:
        return start_date.year

def is_membership_active(membership) -> bool:
    from datetime import date
    return membership.end_date >= date.today()


def is_membership_valid(membership) -> bool:
    """
    Attivo SOLO se:
    - pagato
    - non scaduto
    """
    return membership.is_paid and is_membership_active(membership)
