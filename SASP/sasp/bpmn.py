from uuid import uuid4
import xml.etree.ElementTree as ET
import networkx as nx
import math

class BPMN:
    class Element:
        name: str = ''
        id: str = ''
        xml_tag = None
        xml_diagram_tag = None
        
        def __init__(self, name:str=None, id:str=None, border_color:str=None):
            self.name = name or self.name
            self.id = id or f"id{uuid4()}"
            self.border_color = border_color
        
        def __hash__(self) -> int:
            return hash(self.id)
        
        def xml_diagram(self) -> ET.Element:
            element = ET.Element(f'{BPMN.xml_diagram_namespace}:{self.xml_diagram_tag}')
            element.set('bpmnElement', self.id)
            element.set('id', f"{self.id}_diagram")
            if self.border_color:
                element.set('color:border-color', self.border_color)
            return element
        def xml(self) -> ET.Element:
            return ET.Element(f'{BPMN.xml_namespace}:{self.xml_tag}', {'id': self.id, 'name': self.name})
        
    class Process(Element):
        xml_tag = 'process'
        xml_diagram_tag = 'BPMNPlane'
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.elements = []
        
        def add_element(self, element: 'BPMN.Element'):
            if element not in self.elements:
                self.elements.append(element)
        def remove_element(self, element: 'BPMN.Element'):
            if element in self.elements:
                self.elements.remove(element)
        
        def xml_diagram(self) -> ET.Element:
            element = super().xml_diagram()
            element.set('bpmnElement', self.id)
            element.set('id', f"{self.id}_diagram")
            for e in self.elements:
                element.append(e.xml_diagram())
            return element
        
        def xml(self) -> ET.Element:
            element = super().xml()
            element.set('isExecutable', 'false')
            element.set('isClosed', 'false')
            element.set('processType', 'None')
            for e in self.elements:
                element.append(e.xml())
            return element
    class Diagram(Element):
        elements = []
        xml_diagram_tag = 'BPMNDiagram'
        name = 'diagram'
        process = None
        def __init__(self, process=None, **kwargs):
            self.process = process or BPMN.Process()
            super().__init__(**kwargs)
        
        def xml_diagram(self) -> ET.Element:
            element = super().xml_diagram()
            element.append(self.process.xml_diagram())
            return element
    class Node(Element):
        coord_x = 0
        coord_y = 0
        height = None
        width = None
        xml_diagram_tag = 'BPMNShape'
        xml_bounds_namespace = 'dc'
        xml_bounds_tag = 'Bounds'
        xml_incoming_tag = 'incoming'
        xml_outgoing_tag = 'outgoing'
        
        def __init__(
            self, 
            coord_x=None, 
            coord_y=None, 
            height=None, 
            width=None, 
            process:'BPMN.Process'=None, 
            background_color:str=None,
            **kwargs):
            self.coord_x = coord_x or self.coord_x
            self.coord_y = coord_y or self.coord_y
            self.height = height or self.height
            self.width = width or self.width
            self.incoming = []
            self.outgoing = []
            
            self.background_color = background_color
            
            super().__init__(**kwargs)
            if process:
                process.add_element(self)
        
        def add_incoming(self, edge: 'BPMN.Edge'):
            if edge not in self.incoming:
                self.incoming.append(edge)
        def remove_incoming(self, edge: 'BPMN.Edge'):
            if edge in self.incoming:
                self.incoming.remove(edge)
        def add_outgoing(self, edge: 'BPMN.Edge'):
            if edge not in self.outgoing:
                self.outgoing.append(edge)
        def remove_outgoing(self, edge: 'BPMN.Edge'):
            if edge in self.outgoing:
                self.outgoing.remove(edge)
        
        def xml_diagram(self) -> ET.Element:
            element = super().xml_diagram()
            
            if self.background_color:
                element.set('color:background-color', self.background_color)
            
            bounds = ET.Element(f'{self.xml_bounds_namespace}:{self.xml_bounds_tag}')
            bounds.set('height', str(self.height))
            bounds.set('width', str(self.width))
            bounds.set('x', str(self.coord_x))
            bounds.set('y', str(self.coord_y))
            element.append(bounds)
            return element
        def xml(self) -> ET.Element:
            element = super().xml()
            for e in self.incoming:
                edge = ET.Element(f'{BPMN.xml_namespace}:{self.xml_incoming_tag}')
                edge.text = e.id
            for e in self.outgoing:
                edge = ET.Element(f'{BPMN.xml_namespace}:{self.xml_outgoing_tag}')
                edge.text = e.id
            return element
        
    class Edge(Element):
        xml_diagram_tag = 'BPMNEdge'
        xml_waypoint_namespace = 'di'
        xml_waypoint_tag = 'waypoint'
        
        @property
        def waypoints(self):
            angle = math.atan2((self.target.coord_y - self.source.coord_y)*-1, self.target.coord_x - self.source.coord_x)
            angle = angle % (2 * math.pi)
            if math.pi / 4 <= angle < 3 * math.pi / 4:
                source_x = self.source.coord_x + self.source.width/2
                source_y = self.source.coord_y
                target_x = self.target.coord_x + self.target.width/2
                target_y = self.target.coord_y + self.target.height
            elif 3 * math.pi / 4 <= angle < 5 * math.pi / 4:
                source_x = self.source.coord_x
                source_y = self.source.coord_y + self.source.height/2
                target_x = self.target.coord_x + self.target.width
                target_y = self.target.coord_y + self.target.height/2
            elif 5 * math.pi / 4 <= angle < 7 * math.pi / 4:
                source_x = self.source.coord_x + self.source.width/2
                source_y = self.source.coord_y + self.source.height
                target_x = self.target.coord_x + self.target.width/2
                target_y = self.target.coord_y
            else:
                source_x = self.source.coord_x + self.source.width
                source_y = self.source.coord_y + self.source.height/2
                target_x = self.target.coord_x
                target_y = self.target.coord_y + self.target.height/2
            return [(source_x, source_y), (target_x, target_y)]
            # return [
            #     (self.source.coord_x + self.source.width, self.source.coord_y + self.source.height / 2),
            #     (self.target.coord_x, self.target.coord_y + self.target.height / 2)
            # ]
        
        def __init__(
            self, 
            source:'BPMN.Node'=None, 
            target:'BPMN.Node'=None, 
            process:'BPMN.Process'=None,
            **kwargs):
            self.source = source or self.source
            self.target = target or self.target
            super().__init__(**kwargs)
            if source:
                source.add_outgoing(self)
            if target:
                target.add_incoming(self)
            if process:
                process.add_element(self)
        
        def xml_diagram(self) -> ET.Element:
            element = super().xml_diagram()
            for i, (x, y) in enumerate(self.waypoints):
                waypoint = ET.Element(f'{self.xml_waypoint_namespace}:{self.xml_waypoint_tag}')
                waypoint.set('x', str(x))
                waypoint.set('y', str(y))
                element.append(waypoint)
            return element
        def xml(self) -> ET.Element:
            element = super().xml()
            element.set('sourceRef', self.source.id)
            element.set('targetRef', self.target.id)
            return element
    
    class Flow(Edge):
        pass
    class Event(Node):
        height = 30
        width = 30
    class Gateway(Node):
        height = 60
        width = 60
        direction = 'unspecified'
        
        def __init__(self, direction=None, **kwargs):
            self.direction = direction or self.direction
            super().__init__(**kwargs)
        
        def xml(self) -> ET.Element:
            element = super().xml()
            element.set('gatewayDirection', self.direction)
            return element
    class Activity(Node):
        height = 60
        width = 120
    class Task(Activity):
        xml_tag = 'task'
    class StartEvent(Event):
        xml_tag = 'startEvent'
        pass
    class EndEvent(Event):
        xml_tag = 'endEvent'
        pass
    class ParallelGateway(Gateway):
        xml_tag = 'parallelGateway'
        pass
    class ExclusiveGateway(Gateway):
        xml_tag = 'exclusiveGateway'
        pass
    class InclusiveGateway(Gateway):
        xml_tag = 'inclusiveGateway'
        pass
    class SequenceFlow(Flow):
        xml_tag = 'sequenceFlow'
        pass
    
    xml_namespace = 'bpmn'
    xml_diagram_namespace = 'bpmndi'
    def __init__(self, process=None):
        self.process = process or BPMN.Process()
        self.diagram = BPMN.Diagram(process=self.process)
        self.warnings = []
    
    def networkx(self):
        G = nx.DiGraph()
        for e in self.process.elements:
            if isinstance(e, BPMN.Node):
                type_ = None
                if isinstance(e, BPMN.StartEvent):
                    type_ = 'start'
                elif isinstance(e, BPMN.EndEvent):
                    type_ = 'end'
                elif isinstance(e, BPMN.Task):
                    type_ = 'task'
                elif isinstance(e, BPMN.ParallelGateway):
                    type_ = 'parallel'
                elif isinstance(e, BPMN.Gateway):
                    type_ = 'gateway'
                else:
                    type_ = 'node'
                G.add_node(e.id, name=e.name, type_=type_)
        for e in self.process.elements:
            if isinstance(e, BPMN.Edge):
                G.add_edge(e.source.id, e.target.id)
        return G

    def xml(self):
        root = ET.Element(f'{self.xml_namespace}:definitions', {
            'xmlns:bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'xmlns:bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'xmlns:dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'xmlns:di': 'http://www.omg.org/spec/DD/20100524/DI',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xmlns:color':"http://www.omg.org/spec/BPMN/non-normative/color/1.0",
            'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
            'targetNamespace': 'http://www.signavio.com/bpmn20',
            'typeLanguage': 'http://www.w3.org/2001/XMLSchema',
            'expressionLanguage': 'http://www.w3.org/1999/XPath'
        })
        root.append(self.diagram.xml_diagram())
        root.append(self.process.xml())
        xml_str = ET.tostring(root, encoding='utf-8', method='xml', xml_declaration=True)
        return xml_str
    
    def layout(self, orientation='horizontal', x_scale=None, y_scale=None, grid_x=200, grid_y=200):
        """Layout the BPMN diagram"""
        G = self.networkx()
        # Catch empty graph
        if G.number_of_nodes() == 0:
            self.warnings.append("Empty graph")
            return
        start_node = [n for n, d in G.in_degree() if d == 0 and G.nodes[n]['type_'] == 'start']
        if not start_node:
            self.warnings.append("No start node found")
            return
        start_node = start_node[0]
        # Cast to undirected graph
        G = G.to_undirected()
        G = G.subgraph(nx.node_connected_component(G, start_node))
        pos = nx.drawing.layout.bfs_layout(G, start_node)
        
        # Graph density
        density = min(max(G.number_of_nodes()//10, 1),5)
        if x_scale is None:
            x_scale = 600 * density
        if y_scale is None:
            y_scale = 200 * density
        
        disconnected_nodes = 0
        for e in self.process.elements:
            if isinstance(e, BPMN.Node):
                if e.id not in pos:
                    self.warnings.append(f"Element {e.id} not connected to the start node")
                    e.coord_x = disconnected_nodes
                    e.coord_y = 2*y_scale + e.height
                    disconnected_nodes += (e.width * 1.5)
                else:
                    # Coords are from -1 to 1 so we need to scale them
                    e.coord_x = (pos[e.id][0] + 1) * x_scale
                    e.coord_y = (pos[e.id][1] + 1) * y_scale
                
                # Snap to grid
                # e.coord_x = round(e.coord_x / grid_x) * grid_x + ((grid_x-e.width) / 2)
                # e.coord_y = round(e.coord_y / grid_y) * grid_y + ((grid_y-e.height) / 2)