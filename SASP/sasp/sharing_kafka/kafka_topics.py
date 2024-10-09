import json
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, UUID4, Field, ConfigDict
from datetime import datetime


class Message(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: UUID4 = Field(format="uuid", default_factory=uuid4)
    subject: str = Field(min_length=1)
    sender: str = Field(alias="from", min_length=1)
    recipient: str = Field(alias="to", min_length=1)
    text: str = Field(min_length=1)
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class SASPPlaybook(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: UUID4 = Field(format="uuid", default_factory=uuid4)
    playbook_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    # List of labels can be empty
    labels: list[str] = Field(default_factory=list)
    version: str = Field(min_length=1)
    standard: str = Field(min_length=1)
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    published_by: str = Field(min_length=1)

    playbook_json: str = Field(min_length=1)


if __name__ == '__main__':
    print(json.dumps(Message.model_json_schema(), indent=2))

    message: Message = Message(
                               subject="Python Kafka Message",
                               sender="python.kafka.producer@project.eu",
                               recipient="kafka.consumer.project.eu",
                               text="Python Test Message")

    print(message.model_dump_json(by_alias=True, indent=2))
    print(json.dumps(message.model_dump(mode="json", by_alias=True), indent=2))

    message_from_json: Message = Message.model_validate_json(message.model_dump_json(by_alias=True, indent=2))

    print("Message from JSON: " + message_from_json.model_dump_json(by_alias=True, indent=2))
