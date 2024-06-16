"""View and import/export data from the database via registered :class:`data_import.DataImporter` and :class:`data_export.DataExporter`."""

_racecontext = None

@property
def exporters():
    """`Read Only` All registered exporters.

    :return: A list of :class:`data_export.DataExporter`
    :rtype: list[DataExporter]
    """
    return _racecontext.export_manager.exporters

def run_export(exporter_id):
    """Run selected exporter.

    :param exporter_id: Identifier of exporter to run
    :type exporter_id: str
    :return: Returns output of exporter or False if error.
    :rtype: str|bool
    """
    return _racecontext.export_manager.export(exporter_id)

@property
def importers():
    """`Read Only` All registered importers.

    :return: A list of :class:`data_import.DataImporter`
    :rtype: list[DataImporter]
    """
    return _racecontext.import_manager.importers

def run_import(importer_id, data, import_args=None):
    """_summary_

    :param importer_id: Identifier of importer to run
    :type importer_id: str
    :param data: Data to import
    :type data: any
    :param import_args: Arguments passed to the importer, overrides defaults, defaults to None
    :type import_args: any, optional
    :return: Returns output of importer or False if error.
    :rtype: dict|bool
    """
    return _racecontext.import_manager.run_import(importer_id, data, import_args)