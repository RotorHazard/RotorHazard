from flask.blueprints import Blueprint


def createBlueprint(sample_listener):
    APP = Blueprint('rssi', __name__)

    @APP.route('/rssi')
    def rssi_data():
        rssis_by_node = sample_listener.get_rssis()
        lifetimes_by_node = sample_listener.get_lifetimes()
        nodes = set()
        nodes.update(rssis_by_node)
        nodes.update(lifetimes_by_node)
        payload = {}
        for node in sorted(nodes):
            node_samples = {}
            rssi_samples = rssis_by_node.get(node)
            if rssi_samples:
                node_samples['rssi'] = [{'t': s[0], 'y': s[1]} for s in rssi_samples]
            lifetime_samples = lifetimes_by_node.get(node)
            if lifetime_samples:
                node_samples['lifetime'] = [{'t': s[0], 'y': s[1]} for s in lifetime_samples]
            payload[str(node)] = node_samples
        return payload

    return APP
