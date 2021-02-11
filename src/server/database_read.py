

class DatabaseReader:
    def __init__(self,Database,Pagecache):
        self._Database = Database # Private
        self._Pagecache = Pagecache # Private

    def get_all_pilots(self):
        return self._Database.Pilot.query.all()

    def get_all_heats(self):
        return self._Database.Heat.query.all()

    def get_race_class(self, heat_class_id):
        return self._Database.RaceClass.query.get(heat_class_id)

    def get_heat_nodes_filtered(self, heat_id):
        return self._Database.HeatNode.query.filter_by(heat_id=heat_id)

    def get_head_nodes_f_orderNode(self, heat_id):
        hnf= self.get_heat_nodes_filtered(heat_id)
        return hnf.order_by(self._Database.HeatNode.node_index).all()

    def get_heat_pilot_callsign(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id).callsign




