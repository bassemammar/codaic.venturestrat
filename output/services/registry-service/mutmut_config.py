"""Configuration for mutmut mutation testing."""


def pre_mutation(context):
    """Pre-mutation hook to skip certain mutations."""
    line = context.current_source_line.strip()

    # Skip mutations on imports and type checking
    if line.startswith(('import ', 'from ', 'if TYPE_CHECKING')):
        context.skip = True

    # Skip mutation on class definition lines
    if line.startswith('class ') and line.endswith(':'):
        context.skip = True

    # Skip mutation on function definition lines
    if line.strip().startswith('def ') and line.endswith(':'):
        context.skip = True


def post_mutation(context):
    """Post-mutation hook (optional)."""
    pass