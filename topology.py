from mininet.topo import Topo

class UDPTopology(Topo):
    def build(self):
        # Create three switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Create two hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Connect hosts to switches
        self.addLink(s1, s2)
        self.addLink(s1, s3)
        self.addLink(s2, s3)
        self.addLink(h1, s1)
        self.addLink(h2, s3)



topos = {
    'udptopology': lambda: UDPTopology()
}

