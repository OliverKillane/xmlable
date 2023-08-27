from dataclasses import dataclass
from pathlib import Path
from xmlable import (
    xmlify,
    parse_file,
    write_xml_value,
    write_xml_template,
    write_xsd,
)

THIS_DIR = Path(__file__).parent


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


write_xsd(THIS_DIR / "config.xsd", BigConfig)
write_xml_template(THIS_DIR / "config_xml_template.xml", BigConfig)

original: BigConfig = BigConfig(
    machine_ids={
        MachineID("apac", "abacus"): MachineConfig("71.35.186.234", 24, 2),
        MachineID("apac", "goat"): MachineConfig("75.174.245.110", 34, 2),
        MachineID("fr", "palm"): MachineConfig("58.175.90.125", 78),
    },
    show_logs=True,
)

write_xml_value(THIS_DIR / "config_xml_example.xml", original)

read_config: BigConfig = parse_file(
    BigConfig, THIS_DIR / "config_xml_example.xml"
)

assert read_config == original
