import json
from confluent_kafka import Producer, Consumer, TopicPartition, OFFSET_BEGINNING
from confluent_kafka.serialization import StringSerializer, SerializationContext, MessageField, StringDeserializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer, JSONDeserializer
from .kafka_topics import SASPPlaybook

from django.contrib.auth.models import User

from pathlib import Path

base_path = Path(__file__).parent

class KafkaInterface:
    def __init__(self, user):
        if user.is_anonymous:
            user = User.objects.get(username='default')
        self.user = user
        config = user.profile.logins.get(name='kafka').additional_fields
        
        self.producer = Producer({
            "client.id": config['client.id'],
            "bootstrap.servers": config['bootstrap_servers'],
            "security.protocol": "SSL",
            "ssl.ca.location": config['ssl.ca.location'],
            "ssl.certificate.location": config['ssl.certificate.location'],
            "ssl.key.location": config['ssl.key.location'],
            "ssl.key.password": config['ssl.key.password']
        })
        self.consumer = Consumer({
            "client.id": config['client.id'],
            "group.id": config['group.id'],
            "bootstrap.servers": config['bootstrap_servers'],
            "auto.offset.reset": "earliest",
            "security.protocol": "SSL",
            "ssl.ca.location": config['ssl.ca.location'],
            "ssl.certificate.location": config['ssl.certificate.location'],
            "ssl.key.location": config['ssl.key.location'],
            "ssl.key.password": config['ssl.key.password']
        })
        self.registry = SchemaRegistryClient({
            "url": config['registry.url'],
            "ssl.ca.location": config['ssl.ca.location'],
            "ssl.certificate.location": config['ssl.certificate.location'],
            "ssl.key.location": config['registry.plain.ssl.key.location']
        })
    
    def produce_playbook(self, playbook: SASPPlaybook):
        json_schema: str = json.dumps(SASPPlaybook.model_json_schema(), indent=2)
        json_serializer = JSONSerializer(json_schema, self.registry, conf={"subject.name.strategy": lambda ctx, _: ctx.topic})

        topic: str = SASPPlaybook.__name__

        self.producer.produce(topic=topic,
                        key=StringSerializer()(str(playbook.id)),
                        value=json_serializer(playbook.model_dump(mode="json", by_alias=True),
                                            SerializationContext(topic, MessageField.VALUE)))

        self.producer.flush()

    def get_playbooks(self):
        json_schema: str = json.dumps(SASPPlaybook.model_json_schema(), indent=2)
        json_deserializer = JSONDeserializer(json_schema)

        topic: str = SASPPlaybook.__name__
        topic_partition: TopicPartition = TopicPartition(topic, 0, OFFSET_BEGINNING)
        self.consumer.assign([topic_partition])
        self.consumer.subscribe([topic])

        playbooks = dict()
        while True:
            record = self.consumer.poll(1.0)
            if record is None:
                break
            try:
                key = StringDeserializer()(record.key())
                value = json_deserializer(record.value(), SerializationContext(record.topic(), MessageField.VALUE))
                playbooks[key] = value
            except Exception:
                continue
        return playbooks

    def get_playbook(self, key: str):
        return self.get_playbooks().get(key)