"""VentureStrat Forge — spec file generator."""

import logging
import os
import re
from datetime import date

from src.models import Requirement

logger = logging.getLogger(__name__)


class SpecGenerator:
  """Generates .agent-os spec files from requirements."""

  def generate_spec(self, requirement: Requirement, platform_root: str) -> str:
    """Create spec folder with spec.md and tasks.md. Returns spec name."""
    today = date.today().isoformat()
    slug = self._slugify(requirement.title)
    spec_name = f'{today}-{slug}'
    spec_dir = os.path.join(platform_root, '.agent-os', 'specs', spec_name)

    os.makedirs(spec_dir, exist_ok=True)

    # Write spec.md
    spec_md = self._generate_spec_md(requirement, today)
    with open(os.path.join(spec_dir, 'spec.md'), 'w') as f:
      f.write(spec_md)

    # Write tasks.md
    tasks_md = self._generate_tasks_md(requirement)
    with open(os.path.join(spec_dir, 'tasks.md'), 'w') as f:
      f.write(tasks_md)

    logger.info(f'Generated spec at {spec_dir}')
    return spec_name

  def _slugify(self, title: str) -> str:
    """Convert title to kebab-case, max 5 words."""
    # Lowercase and replace non-alphanumeric with spaces
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
    words = cleaned.split()[:5]
    return '-'.join(words)

  def _generate_spec_md(self, requirement: Requirement, today: str) -> str:
    """Generate spec.md content."""
    return f"""# Spec Requirements Document

> Spec: {requirement.title}
> Created: {today}
> Status: Planning
> Source: Forge ({requirement.requirement_id})

## Overview

{requirement.description or requirement.title}

## Spec Scope

1. **{requirement.title}** - {requirement.description or 'Implementation as specified'}

## Expected Deliverable

1. Feature implemented and tested
2. All tests passing
"""

  def _generate_tasks_md(self, requirement: Requirement) -> str:
    """Generate tasks.md based on requirement type."""
    header = f"""# Spec Tasks

These are the tasks for the spec: {requirement.title}

**Workflow Type:** {requirement.requirement_type}
**Source:** Forge ({requirement.requirement_id})

> Created: {date.today().isoformat()}
> Status: Ready for Implementation

"""

    if requirement.requirement_type == 'bug_fix':
      return header + """<!-- wave: 1, parallel: false -->
- [ ] 1. Reproduce and Diagnose
  - [ ] 1.1 Reproduce the reported issue
  - [ ] 1.2 Identify root cause
  - [ ] 1.3 Document reproduction steps

<!-- wave: 2, parallel: false, depends: 1 -->
- [ ] 2. Write Failing Test
  - [ ] 2.1 Write test that captures the bug
  - [ ] 2.2 Verify test fails with current code

<!-- wave: 3, parallel: false, depends: 2 -->
- [ ] 3. Fix Implementation
  - [ ] 3.1 Implement the fix
  - [ ] 3.2 Verify failing test now passes
  - [ ] 3.3 Run full test suite

<!-- wave: 4, parallel: false, depends: 3 -->
- [ ] 4. Verify and Ship
  - [ ] 4.1 Manual verification
  - [ ] 4.2 Commit and push
"""

    elif requirement.requirement_type == 'enhancement':
      return header + """<!-- wave: 1, parallel: false -->
- [ ] 1. Analyze Existing Code
  - [ ] 1.1 Review current implementation
  - [ ] 1.2 Identify integration points
  - [ ] 1.3 Plan enhancement approach

<!-- wave: 2, parallel: false, depends: 1 -->
- [ ] 2. Write Tests
  - [ ] 2.1 Write tests for new functionality
  - [ ] 2.2 Verify tests fail (TDD)

<!-- wave: 3, parallel: false, depends: 2 -->
- [ ] 3. Implement Enhancement
  - [ ] 3.1 Implement changes
  - [ ] 3.2 Verify new tests pass
  - [ ] 3.3 Run full test suite

<!-- wave: 4, parallel: false, depends: 3 -->
- [ ] 4. Verify and Ship
  - [ ] 4.1 Manual verification
  - [ ] 4.2 Commit and push
"""

    else:
      # new_feature (default)
      return header + """<!-- wave: 1, parallel: false -->
- [ ] 1. Design
  - [ ] 1.1 Define data models
  - [ ] 1.2 Define API contracts
  - [ ] 1.3 Define UI components

<!-- wave: 2, parallel: false, depends: 1 -->
- [ ] 2. Write Tests
  - [ ] 2.1 Write unit tests
  - [ ] 2.2 Write integration tests
  - [ ] 2.3 Verify tests fail (TDD)

<!-- wave: 3, parallel: false, depends: 2 -->
- [ ] 3. Implement
  - [ ] 3.1 Implement backend
  - [ ] 3.2 Implement frontend
  - [ ] 3.3 Verify all tests pass

<!-- wave: 4, parallel: false, depends: 3 -->
- [ ] 4. Verify and Ship
  - [ ] 4.1 End-to-end testing
  - [ ] 4.2 Commit and push
"""
