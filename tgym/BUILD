package(default_visibility = ["//visibility:public"])

# load("@pip_deps//:requirements.bzl", "requirement")
# load("@rules_python//python:defs.bzl", "py_test", "py_library")

py_library(
    name = "py_logger_lib",
    srcs = [
        "logger.py",
    ],
    deps = [],
)

py_library(
    name = "py_default_lib",
    srcs = [
        "market.py",
        "portfolio.py",
    ],
    deps = [
        "//tgym:py_logger_lib",
    ],
)

py_library(
    name = "py_scenario_lib",
    srcs = [
        "scenario.py",
    ],
    deps = [
        "//tgym:py_default_lib",
    ],
)

py_test(
    name = "market_test",
    srcs = ["market_test.py"],
    deps = [
        ":py_default_lib",
        ":py_logger_lib",
    ],
)
