from datetime import date

# From 16 September (included) the enrollment/renewal is considered "early":
# the member receives both the current-year card and the following-year card.
# 16 September is the first day of the European Mobility Week.
EARLY_RENEWAL_START = (9, 16)


def is_early_renewal(start_date: date) -> bool:
    """True when the enrollment/renewal falls in the early-renewal window
    (from 16 September to 31 December). In that case the member receives both
    the card for the current year and the card for the following year."""
    return (start_date.month, start_date.day) >= EARLY_RENEWAL_START


def calculate_membership_period(start_date: date):
    if is_early_renewal(start_date):
        end_year = start_date.year + 1
    else:
        end_year = start_date.year

    return start_date, date(end_year, 12, 31)


def calculate_reference_year(start_date: date):
    if is_early_renewal(start_date):
        return start_date.year + 1
    else:
        return start_date.year


def calculate_membership_periods(start_date: date):
    """Return the list of ``(start_date, end_date, reference_year)`` periods to issue.

    - Outside the early-renewal window: a single card covering the current year.
    - In the early-renewal window (from 16 September): two cards, one for the
      current year (valid until 31/12 of the current year) and one for the
      following year (valid for the whole next year).
    """
    current_year = start_date.year

    periods = [
        (start_date, date(current_year, 12, 31), current_year),
    ]

    if is_early_renewal(start_date):
        next_year = current_year + 1
        periods.append((date(next_year, 1, 1), date(next_year, 12, 31), next_year))

    return periods


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
