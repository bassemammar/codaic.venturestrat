"""ValidationService — cross-document business rule validation.

Enforces equity caps, share limits, entity consistency, and email matching
rules across legal entities, persons, and documents.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ValidationError:
  """A single validation error or warning."""
  rule_id: str
  severity: str  # CRITICAL, HIGH, MEDIUM, LOW
  message: str
  field: str
  blocking: bool


@dataclass
class ValidationResult:
  """Aggregated validation result."""
  valid: bool
  errors: list[ValidationError] = field(default_factory=list)
  warnings: list[ValidationError] = field(default_factory=list)


# Protected fields that cannot change when documents reference the entity
PROTECTED_FIELDS = {'legal_name', 'jurisdiction'}


class ValidationService:
  """Static validation methods for cross-document business rules."""

  @staticmethod
  def validate_equity_total(
    holdings: list[dict],
    authorized_shares: int | None,
  ) -> ValidationResult:
    """Validate equity holdings for a legal entity.

    Rule 2.1: Total percentage must not exceed 100%.
    Rule 2.2: Total issued shares must not exceed authorized shares.

    Args:
      holdings: List of dicts with 'percentage' and optionally 'number_of_shares'.
      authorized_shares: Company's authorized share count (None = unlimited).

    Returns:
      ValidationResult with any errors found.
    """
    errors: list[ValidationError] = []

    if not holdings:
      return ValidationResult(valid=True)

    # Rule 2.1: Total percentage <= 100%
    total_pct = sum(Decimal(str(h['percentage'])) for h in holdings)
    if total_pct > Decimal('100.00'):
      errors.append(ValidationError(
        rule_id='2.1',
        severity='CRITICAL',
        message=f'Total equity percentage is {total_pct}%, exceeds 100%',
        field='percentage',
        blocking=True,
      ))

    # Rule 2.2: Total shares <= authorized (if authorized is set)
    if authorized_shares is not None:
      total_shares = sum(h.get('number_of_shares', 0) for h in holdings)
      if total_shares > authorized_shares:
        errors.append(ValidationError(
          rule_id='2.2',
          severity='CRITICAL',
          message=f'Total issued shares ({total_shares}) exceeds authorized ({authorized_shares})',
          field='number_of_shares',
          blocking=True,
        ))

    return ValidationResult(
      valid=len(errors) == 0,
      errors=errors,
    )

  @staticmethod
  def validate_person_email(
    email: str,
    existing_founders: list[dict],
  ) -> ValidationResult:
    """Check if new person's email matches an existing founder.

    Rule 1.3: Warn if email matches existing founder (HIGH severity, non-blocking).

    Args:
      email: Email of the person being created/updated.
      existing_founders: List of dicts with 'email' for existing founders.

    Returns:
      ValidationResult with warnings if match found.
    """
    warnings: list[ValidationError] = []
    email_lower = email.lower()

    for founder in existing_founders:
      if founder.get('email', '').lower() == email_lower:
        warnings.append(ValidationError(
          rule_id='1.3',
          severity='HIGH',
          message=f'Person {email} has same email as existing founder',
          field='email',
          blocking=False,
        ))
        break

    return ValidationResult(
      valid=True,  # warnings don't block
      warnings=warnings,
    )

  @staticmethod
  def validate_company_update(
    field: str,
    has_generated_documents: bool,
  ) -> ValidationResult:
    """Check if a company field change is allowed.

    Rule 1.1: Cannot change legal_name or jurisdiction if referenced
    in generated documents.

    Args:
      field: Field name being changed.
      has_generated_documents: Whether the company has generated documents.

    Returns:
      ValidationResult blocking the change if applicable.
    """
    errors: list[ValidationError] = []

    if field in PROTECTED_FIELDS and has_generated_documents:
      errors.append(ValidationError(
        rule_id='1.1',
        severity='CRITICAL',
        message=f'Cannot change {field} — entity is referenced in generated documents',
        field=field,
        blocking=True,
      ))

    return ValidationResult(
      valid=len(errors) == 0,
      errors=errors,
    )
