"""View and Generate heats via registered :class:`HeatGenerator.HeatGenerator`."""

from RHUtils import callWithDatabaseWrapper

_racecontext = None

@property
def generators():
    """`Read Only` All registered generators.

    :return: A list of :class:`HeatGenerator.HeatGenerator`
    :rtype: list[HeatGenerator]
    """
    return _racecontext.heat_generate_manager.generators

@callWithDatabaseWrapper
def generate(generator_id, generate_args):
    """Run selected generator, creating heats and race classes as needed.

    :param generator_id: Identifier of generator to run
    :type generator_id: str
    :param generate_args: Arguments passed to the generator, overrides defaults
    :type generate_args: dict
    :return: Returns output of generator or False if error.
    :rtype: str|bool
    """
    return _racecontext.heat_generate_manager.generate(generator_id, generate_args)