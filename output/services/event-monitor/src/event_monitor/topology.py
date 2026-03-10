"""Topology graph builder from service manifest.yaml files."""

from __future__ import annotations

from pathlib import Path

import structlog
import yaml

from event_monitor.models import TopologyEdge, TopologyGraph, TopologyNode

logger = structlog.get_logger(__name__)

# Service accent colors
SERVICE_COLORS: dict[str, str] = {
  'investor-service': '#3f51b5',
  'outreach-service': '#00897b',
  'crm-service': '#e65100',
  'billing-service': '#1565c0',
}


def build_topology(services_dir: str) -> TopologyGraph:
  """Parse all manifest.yaml files and build a topology graph.

  Returns a graph with service nodes, topic nodes, and edges
  showing which services produce/consume which topics.
  """
  services_path = Path(services_dir)
  nodes: dict[str, TopologyNode] = {}
  edges: list[TopologyEdge] = []

  # Scan all service directories for manifest.yaml
  if not services_path.exists():
    logger.warning('services_dir_not_found', path=services_dir)
    return TopologyGraph(nodes=[], edges=[])

  for manifest_path in sorted(services_path.glob('*/manifest.yaml')):
    try:
      manifest = yaml.safe_load(manifest_path.read_text())
    except Exception as exc:
      logger.warning('manifest_parse_failed', path=str(manifest_path), error=str(exc))
      continue

    service_name = manifest.get('name', manifest_path.parent.name)
    service_id = f'svc:{service_name}'

    # Add service node
    nodes[service_id] = TopologyNode(
      id=service_id,
      type='service',
      label=service_name,
      color=SERVICE_COLORS.get(service_name, '#9e9e9e'),
      metadata={
        'version': manifest.get('version', ''),
        'port': _get_port(manifest),
      },
    )

    # Parse provides.events → outgoing edges (service → topic)
    provides = manifest.get('provides', {}) or {}
    for evt in (provides.get('events', []) or []):
      topic = evt.get('topic', '') if isinstance(evt, dict) else str(evt)
      if not topic:
        continue
      topic_id = f'topic:{topic}'
      if topic_id not in nodes:
        schema = evt.get('schema', '') if isinstance(evt, dict) else ''
        nodes[topic_id] = TopologyNode(
          id=topic_id,
          type='topic',
          label=topic,
          metadata={'schema': schema},
        )
      edges.append(TopologyEdge(
        source=service_id,
        target=topic_id,
        label='produces',
      ))

    # Parse consumes.events → incoming edges (topic → service)
    consumes = manifest.get('consumes', {}) or {}
    for evt in (consumes.get('events', []) or []):
      topic = evt.get('topic', '') if isinstance(evt, dict) else str(evt)
      if not topic:
        continue
      topic_id = f'topic:{topic}'
      if topic_id not in nodes:
        schema = evt.get('schema', '') if isinstance(evt, dict) else ''
        nodes[topic_id] = TopologyNode(
          id=topic_id,
          type='topic',
          label=topic,
          metadata={'schema': schema},
        )
      edges.append(TopologyEdge(
        source=topic_id,
        target=service_id,
        label='consumes',
        animated=True,
      ))

  return TopologyGraph(
    nodes=list(nodes.values()),
    edges=edges,
  )


def _get_port(manifest: dict) -> int | None:
  """Extract port from manifest metadata or health config."""
  health = manifest.get('health', {})
  # Try to get port from service configuration
  metadata = manifest.get('metadata', {})
  return metadata.get('port')
