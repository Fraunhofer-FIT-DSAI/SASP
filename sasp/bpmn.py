from uuid import uuid4
import xml.etree.ElementTree as ET

class BPMN:
    class Element:
        name: str = ''
        id: str = ''
        xml_tag = None
        xml_diagram_tag = None
        
        def __init__(self, name:str=None, id:str=None):
            self.name = name or self.name
            self.id = id or f"id{uuid4()}"
        
        def __hash__(self) -> int:
            return hash(self.id)
        
        def xml_diagram(self) -> ET.Element:
            return ET.Element(f'{BPMN.xml_diagram_namespace}:{self.xml_diagram_tag}')
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
        xml_bounds_namespace = 'omgdc'
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
            **kwargs):
            self.coord_x = coord_x or self.coord_x
            self.coord_y = coord_y or self.coord_y
            self.height = height or self.height
            self.width = width or self.width
            self.incoming = []
            self.outgoing = []
            
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
            element.set('bpmnElement', self.id)
            element.set('id', f"{self.id}_diagram")
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
        xml_waypoint_namespace = 'omgdi'
        xml_waypoint_tag = 'waypoint'
        
        @property
        def waypoints(self):
            return [
                (self.source.coord_x + self.source.width, self.source.coord_y + self.source.height / 2),
                (self.target.coord_x, self.target.coord_y + self.target.height / 2)
            ]
        
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
            element.set('bpmnElement', self.id)
            element.set('id', f"{self.id}_diagram")
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

    def xml(self):
        # <bpmn:definitions 
        # xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
        # xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" 
        # xmlns:omgdc="http://www.omg.org/spec/DD/20100524/DC" 
        # xmlns:omgdi="http://www.omg.org/spec/DD/20100524/DI" 
        # xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        # xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
        # targetNamespace="http://www.signavio.com/bpmn20" 
        # typeLanguage="http://www.w3.org/2001/XMLSchema" 
        # expressionLanguage="http://www.w3.org/1999/XPath">
        root = ET.Element(f'{self.xml_namespace}:definitions', {
            'xmlns:bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'xmlns:bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'xmlns:omgdc': 'http://www.omg.org/spec/DD/20100524/DC',
            'xmlns:omgdi': 'http://www.omg.org/spec/DD/20100524/DI',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
            'targetNamespace': 'http://www.signavio.com/bpmn20',
            'typeLanguage': 'http://www.w3.org/2001/XMLSchema',
            'expressionLanguage': 'http://www.w3.org/1999/XPath'
        })
        root.append(self.diagram.xml_diagram())
        root.append(self.process.xml())
        
        xml_str = ET.tostring(root, encoding='utf-8', method='xml', xml_declaration=True)
        return xml_str
    
    def layout(self, padding_x=400, padding_y=100, orientation='horizontal'):
        """Layout the BPMN diagram"""
        nodes = [e for e in self.process.elements if isinstance(e, BPMN.Node)]
        visited = set()
        columns = []
        while len(visited) < len(nodes):
            column = []
            for node in nodes:
                if node not in visited and all([e.source in visited for e in node.incoming]):
                    column.append(node)
            column = sorted(column, key=lambda x: len(x.outgoing), reverse=True)
            columns.append(column)
            visited.update(column)
        for i, column in enumerate(columns):
            for j, node in enumerate(column):
                if orientation == 'horizontal':
                    node.coord_x = i * padding_x
                    node.coord_x += (padding_x - node.width) / 2
                    node.coord_y = j * padding_y
                    node.coord_y += (padding_y - node.height) / 2
                else:
                    node.coord_x = j * padding_x
                    node.coord_x += (padding_x - node.width) / 2
                    node.coord_y = i * padding_y
                    node.coord_y += (padding_y - node.height) / 2