from pox.core import core
import pox.openflow.libopenflow_01 as of
from collections import deque

log = core.getLogger()


class RerouteController:

    def __init__(self):
        self.hosts = {}
        self.links = set()

        # Host-facing ports in the current Mininet topology
        self.host_ports = {
            (1, 3),
            (3, 3)
        }

        core.openflow.addListeners(self)
        core.openflow_discovery.addListeners(self)

        log.info("UDP SDN Rerouting Controller Started")

    def _handle_ConnectionUp(self, event):
        log.info("Switch %s connected", event.dpid)

    def _handle_LinkEvent(self, event):
        link = event.link
        edge = (
            (link.dpid1, link.port1),
            (link.dpid2, link.port2)
        )

        if event.added:
            self.links.add(edge)
            log.info("Link added: %s", link)
        else:
            self.links.discard(edge)
            log.warning("Link removed: %s", link)

        # Clear old forwarding rules on every switch
        for connection in core.openflow.connections:
            msg = of.ofp_flow_mod()
            msg.command = of.OFPFC_DELETE
            connection.send(msg)

        log.info("Forwarding rules cleared")

    def _handle_PacketIn(self, event):
        packet = event.parsed

        if not packet or not packet.src or not packet.dst:
            return

        if packet.src.is_multicast:
            return

        dpid = event.dpid
        in_port = event.port

        # Learn only from host-facing ports
        if (dpid, in_port) in self.host_ports:
            self.hosts[packet.src] = (dpid, in_port)

        # Flood broadcasts and unknown destinations
        if packet.dst.is_multicast or packet.dst not in self.hosts:
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.actions.append(
                of.ofp_action_output(port=of.OFPP_FLOOD)
            )
            event.connection.send(msg)
            return

        dst_dpid, dst_port = self.hosts[packet.dst]

        path = self.find_path(dpid, dst_dpid)

        if path is None:
            log.warning("No route available")
            return

        log.info("Route selected: %s", path)

        # Install forwarding rules along the path
        for i, switch in enumerate(path):
            connection = core.openflow.getConnection(switch)

            if connection is None:
                continue

            if i == len(path) - 1:
                out_port = dst_port
            else:
                out_port = self.get_link_port(
                    switch, path[i + 1]
                )

            if out_port is None:
                continue

            match = of.ofp_match()
            match.dl_src = packet.src
            match.dl_dst = packet.dst

            flow = of.ofp_flow_mod()
            flow.match = match
            flow.idle_timeout = 30
            flow.hard_timeout = 60
            flow.actions.append(
                of.ofp_action_output(port=out_port)
            )

            connection.send(flow)

        # Send the current packet along the first hop
        if len(path) > 1:
            first_port = self.get_link_port(dpid, path[1])
        else:
            first_port = dst_port

        if first_port is not None:
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.actions.append(
                of.ofp_action_output(port=first_port)
            )
            event.connection.send(msg)

    def find_path(self, start, end):
        if start == end:
            return [start]

        graph = {}

        for edge in self.links:
            (a, _), (b, _) = edge
            graph.setdefault(a, []).append(b)
            graph.setdefault(b, []).append(a)

        queue = deque([[start]])
        visited = {start}

        while queue:
            path = queue.popleft()
            current = path[-1]

            for neighbour in graph.get(current, []):
                if neighbour == end:
                    return path + [neighbour]

                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(path + [neighbour])

        return None

    def get_link_port(self, source, destination):
        for edge in self.links:
            (a, port_a), (b, port_b) = edge

            if a == source and b == destination:
                return port_a

            if b == source and a == destination:
                return port_b

        return None


def launch():
    core.registerNew(RerouteController)
