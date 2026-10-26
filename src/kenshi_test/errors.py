"""Stable machine-readable failures and CLI exit codes."""


class KenshiTestError(Exception):
    code = "runtime_error"
    exit_code = 3


class ConfigError(KenshiTestError):
    code = "invalid_config"
    exit_code = 2


class AdapterError(KenshiTestError):
    code = "adapter_error"


class TestFailure(KenshiTestError):
    __test__ = False
    code = "assertion_failed"
    exit_code = 1


class OperationTimeout(KenshiTestError):
    code = "timeout"
    exit_code = 4


class GameMissing(KenshiTestError):
    code = "game_missing"
    exit_code = 5


class FeatureUnavailable(KenshiTestError):
    code = "not_implemented"
    exit_code = 6
