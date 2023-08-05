from dataclasses import dataclass
from xmlable import xmlify, write_file, parse_file
from ipconn import IPv4Conn


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
    sessions: dict[str, SessionConfig]
    name_to_user: dict[str, int | UserConfig]


write_file("config.xsd", MyPythonApp.xsd())
write_file("config_xml_template.xml", MyPythonApp.xml())

original = MyPythonApp(
    mainconf=Inspect(
        debug_logs=False,
        metrics_url="http://metricsapi.corp.org",
        control_timeout=23,
        control_port=5788,
    ),
    sessions={
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
    name_to_user={
        "peter bread": 1233,
        "mike rofone": UserConfig("mike_rofone_12", "1224**AAUID"),
        "authur eight": UserConfig("authur_124", "1223**AAUID"),
    },
)
write_file("config_xml_example.xml", original.xml_value())

read_config: MyPythonApp = parse_file(MyPythonApp, "config_xml_example.xml")

assert read_config == original
