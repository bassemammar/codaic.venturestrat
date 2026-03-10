"""FollowUpRepository — persistence layer for FollowUp records."""

from outreach_service.infrastructure.orm.follow_up import FollowUp
from outreach_service.infrastructure.repositories.base_repository import BaseRepository


class FollowUpRepository(BaseRepository[FollowUp]):
  """Repository for FollowUp entities."""

  def __init__(self, session=None):
    super().__init__(FollowUp, session)

  async def find_by_message_id(self, message_id: str) -> list:
    """Return all follow-ups for a given message, ordered by sequence_number."""
    results = await self.search(
      [('message_id', '=', message_id)],
      skip=0,
      limit=100,
    )
    return sorted(results, key=lambda r: getattr(r, 'sequence_number', 0))
