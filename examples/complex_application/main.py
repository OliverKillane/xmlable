from dataclasses import dataclass
from pathlib import Path
from xmlable import (
    xmlify,
    parse_file,
    write_xml_value,
    write_xml_template,
    write_xsd,
)
from ipconn import IPv4Conn

THIS_DIR = Path(__file__).parent


@xmlify
@dataclass
class SessionConfig:
    id: int
    app_name: str
    conn: IPv4Conn


@xmlify
@dataclass
class Inspect:
    debug_logs: bool
    metrics_url: str
    control_timeout: int
    control_port: int


@xmlify
@dataclass
class UserConfig:
    # Users can be id (int) or this dataclass
    name: str
    auth_token: str


@xmlify
@dataclass
class MyPythonApp:
    mainconf: Inspect
    named_sessions: dict[str, SessionConfig]
    extra_sessions: list[SessionConfig]
    name_to_user: dict[str, int | UserConfig]


write_xsd(THIS_DIR / "config.xsd", MyPythonApp)
write_xml_template(THIS_DIR / "config_xml_template.xml", MyPythonApp)

original = MyPythonApp(
    mainconf=Inspect(
        debug_logs=False,
        metrics_url="http://metricsapi.corp.org",
        control_timeout=23,
        control_port=5788,
    ),
    named_sessions={
        "sess_123": SessionConfig(
            id=12334,
            app_name="myotherapp-1.26.2",
            conn=IPv4Conn(protocol="tcp", ip=(1, 1, 1, 23), port=2307),
        ),
        "sess_124": SessionConfig(
            id=12334,
            app_name="myotherapp-1.26.2",
            conn=IPv4Conn(protocol="tcp", ip=(1, 1, 1, 24), port=2308),
        ),
    },
    extra_sessions=[
        SessionConfig(
            id=12335,
            app_name="extra_app-3.15.1",
            conn=IPv4Conn(protocol="quic", ip=(1, 1, 1, 25), port=2307),
        ),
        SessionConfig(
            id=14435,
            app_name="extra_app-3.15.1",
            conn=IPv4Conn(protocol="quic", ip=(1, 1, 1, 26), port=2307),
        ),
    ],
    name_to_user={
        "peter bread": 1233,
        "mike rofone": UserConfig("mike_rofone_12", "1224**AAUID"),
        "authur eight": UserConfig("authur_124", "1223**AAUID"),
    },
)
write_xml_value(THIS_DIR / "config_xml_example.xml", original)

read_config: MyPythonApp = parse_file(
    MyPythonApp, THIS_DIR / "config_xml_example.xml"
)

assert read_config == original
