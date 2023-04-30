from dataclasses import dataclass
from xmlable import xmlify, write_xsd, write_xml, write_xml_value, parse_xml


@xmlify
@dataclass(frozen=True)
class MachineID:
    location: str
    serv_name: str


@xmlify
@dataclass
class MachineConfig:
    ip: str
    cores: int
    org_owner: int | None = None


@xmlify
@dataclass
class BigConfig:
    machine_ids: dict[MachineID, MachineConfig]
    show_logs: bool


write_xsd(BigConfig, "config.xsd")

write_xml(BigConfig, "config_xml_template.xml")

# and now for an example:
write_xml_value(
    BigConfig(
        machine_ids={
            MachineID("apac", "abacus"): MachineConfig("71.35.186.234", 24, 2),
            MachineID("apac", "goat"): MachineConfig("75.174.245.110", 34, 2),
            MachineID("fr", "palm"): MachineConfig("58.175.90.125", 78),
        },
        show_logs=True,
    ),
    "config_xml_example.xml",
)

# and now read it back
config: BigConfig = parse_xml(BigConfig, "config_xml_example.xml")
print(config)
