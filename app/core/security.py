from dataclasses import dataclass


@dataclass
class Principal:
    tenant: str
    owner: str
    groups: list[str]

def get_principal()-> Principal:
    return Principal(tenant="test", owner="test-user-001", groups=["user"])